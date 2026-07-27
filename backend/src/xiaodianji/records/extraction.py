import asyncio
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from xiaodianji.confirmations.service import ConfirmationRecord
from xiaodianji.customers.service import CustomerService
from xiaodianji.evidences.service import EvidenceService, TranscriptInvalid
from xiaodianji.models import PendingConfirmation, RecordCreationReservation
from xiaodianji.providers.base import ASRProvider, ExtractionProvider, ProviderUnavailable
from xiaodianji.records.manual import certain_field_confidences
from xiaodianji.schemas.record import RecordDraft, record_draft_adapter


class CandidateConfirmationWorkflow(Protocol):
    async def create(self, shop_id: UUID, draft: RecordDraft, idempotency_key: str, *, field_confidences: dict[str, str] | None = None, source_evidence_id: UUID | None = None, model_name: str | None = None) -> ConfirmationRecord: ...


class RecordWorkflow:
    def __init__(
        self,
        *,
        confirmation_workflow: CandidateConfirmationWorkflow,
        extraction_provider: ExtractionProvider,
        asr_provider: ASRProvider,
        evidence_service: EvidenceService | None = None,
        customer_service: CustomerService | None = None,
        reservation_lease: timedelta = timedelta(minutes=5),
    ) -> None:
        if reservation_lease <= timedelta(0):
            raise ValueError("reservation lease must be positive")
        self.confirmation_workflow, self.extraction_provider, self.asr_provider = confirmation_workflow, extraction_provider, asr_provider
        self.evidence_service, self.customer_service = evidence_service, customer_service
        self.reservation_lease = reservation_lease
        self.reservation_renew_interval = reservation_lease.total_seconds() / 3

    async def from_text(self, shop_id: UUID, text: str, idempotency_key: str, *, source_evidence_id: UUID | None = None) -> ConfirmationRecord:
        try:
            extraction = await self.extraction_provider.extract(text)
            draft = record_draft_adapter.validate_python(extraction.draft)
            confidences = certain_field_confidences(draft.model_dump(mode="json"))
            confidences.update({field: self._confidence_as_string(value) for field, value in extraction.field_confidences.items()})
        except ProviderUnavailable: raise
        except (AttributeError, InvalidOperation, TypeError, ValidationError, ValueError) as error: raise ProviderUnavailable("extraction provider returned an invalid candidate") from error
        draft = await self._with_customer_match(shop_id, draft)
        return await self.confirmation_workflow.create(shop_id, draft, idempotency_key, field_confidences=confidences, source_evidence_id=source_evidence_id, model_name=extraction.model_name)

    async def from_voice(self, shop_id: UUID, audio: bytes, mime_type: str, original_filename: str | None, idempotency_key: str) -> ConfirmationRecord:
        if self.evidence_service is None: raise RuntimeError("voice recording requires an evidence service")
        async def create_candidate() -> ConfirmationRecord:
            evidence = await self.evidence_service.create_upload(shop_id=shop_id, original_filename=original_filename, mime_type=mime_type, data=audio)
            try:
                transcript_text = (await self.asr_provider.transcribe(audio, evidence.mime_type)).transcript
                await self.evidence_service.attach_transcript(shop_id, evidence.id, transcript_text)
            except ProviderUnavailable: raise
            except (AttributeError, TranscriptInvalid, TypeError, ValueError) as error: raise ProviderUnavailable("ASR transcript is invalid") from error
            return await self.from_text(shop_id, transcript_text, idempotency_key, source_evidence_id=evidence.id)
        if not hasattr(self.confirmation_workflow, "session_factory"):
            return await create_candidate()
        return await self._run_reserved(shop_id, idempotency_key, create_candidate)

    async def _run_reserved(self, shop_id: UUID, idempotency_key: str, create_candidate) -> ConfirmationRecord:
        factory = self.confirmation_workflow.session_factory
        owner_token = uuid4()
        for _ in range(3000):
            async with factory() as session:
                existing = await session.scalar(select(PendingConfirmation).where(PendingConfirmation.shop_id == shop_id, PendingConfirmation.idempotency_key == idempotency_key))
            if existing is not None:
                return self.confirmation_workflow._to_record(existing)
            reservation = (
                insert(RecordCreationReservation)
                .values(
                    shop_id=shop_id,
                    idempotency_key=idempotency_key,
                    owner_token=owner_token,
                    expires_at=func.now() + self.reservation_lease,
                )
                .on_conflict_do_update(
                    constraint="uq_record_reservation_shop_idempotency",
                    set_={
                        "owner_token": owner_token,
                        "expires_at": func.now() + self.reservation_lease,
                    },
                    where=RecordCreationReservation.expires_at <= func.now(),
                )
                .returning(RecordCreationReservation.owner_token)
            )
            async with factory.begin() as session:
                acquired_owner = await session.scalar(reservation)
            if acquired_owner is None:
                await asyncio.sleep(0.01)
                continue
            try:
                async with factory() as session:
                    existing = await session.scalar(select(PendingConfirmation).where(PendingConfirmation.shop_id == shop_id, PendingConfirmation.idempotency_key == idempotency_key))
                if existing is not None:
                    return self.confirmation_workflow._to_record(existing)
                return await self._run_candidate_with_renewal(
                    shop_id,
                    idempotency_key,
                    owner_token,
                    create_candidate,
                )
            finally:
                async with factory.begin() as session:
                    await session.execute(
                        delete(RecordCreationReservation).where(
                            RecordCreationReservation.shop_id == shop_id,
                            RecordCreationReservation.idempotency_key == idempotency_key,
                            RecordCreationReservation.owner_token == owner_token,
                        )
                    )
        raise RuntimeError("record creation is still in progress")

    async def _run_candidate_with_renewal(
        self,
        shop_id: UUID,
        idempotency_key: str,
        owner_token: UUID,
        create_candidate,
    ) -> ConfirmationRecord:
        candidate_task = asyncio.create_task(create_candidate())
        renewal_task = asyncio.create_task(
            self._renew_reservation(shop_id, idempotency_key, owner_token)
        )
        tasks = (candidate_task, renewal_task)
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if renewal_task in done:
                candidate_task.cancel()
                await asyncio.gather(candidate_task, return_exceptions=True)
                await renewal_task
                raise ProviderUnavailable("record creation reservation renewal stopped")
            renewal_task.cancel()
            await asyncio.gather(renewal_task, return_exceptions=True)
            return await candidate_task
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _renew_reservation(
        self,
        shop_id: UUID,
        idempotency_key: str,
        owner_token: UUID,
    ) -> None:
        factory = self.confirmation_workflow.session_factory
        while True:
            await asyncio.sleep(self.reservation_renew_interval)
            renewal = (
                update(RecordCreationReservation)
                .where(
                    RecordCreationReservation.shop_id == shop_id,
                    RecordCreationReservation.idempotency_key == idempotency_key,
                    RecordCreationReservation.owner_token == owner_token,
                    RecordCreationReservation.expires_at > func.now(),
                )
                .values(expires_at=func.now() + self.reservation_lease)
                .returning(RecordCreationReservation.owner_token)
            )
            async with factory.begin() as session:
                renewed_owner = await session.scalar(renewal)
            if renewed_owner != owner_token:
                raise ProviderUnavailable("record creation reservation ownership was lost")

    async def _with_customer_match(self, shop_id: UUID, draft: RecordDraft) -> RecordDraft:
        if self.customer_service is None or not hasattr(draft, "items"): return draft
        matched = await self.customer_service.match(shop_id, draft.customer_name)
        if matched.customer_id is None: return draft
        payload = draft.model_dump(mode="python"); payload["customer_id"] = matched.customer_id
        return record_draft_adapter.validate_python(payload)

    @staticmethod
    def _confidence_as_string(confidence: Decimal) -> str:
        normalized = Decimal(str(confidence))
        if not normalized.is_finite() or not Decimal("0") <= normalized <= Decimal("1"): raise ValueError("confidence must be between zero and one")
        return f"{normalized:.2f}"
