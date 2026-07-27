from decimal import Decimal, InvalidOperation
from typing import Awaitable, Callable, Protocol
from uuid import UUID

from pydantic import ValidationError

from xiaodianji.confirmations.service import ConfirmationRecord
from xiaodianji.customers.service import CustomerService
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.providers.base import ASRProvider, ExtractionProvider, ProviderUnavailable
from xiaodianji.records.manual import certain_field_confidences
from xiaodianji.schemas.record import RecordDraft, record_draft_adapter


class CandidateConfirmationWorkflow(Protocol):
    async def create(self, shop_id: UUID, draft: RecordDraft, idempotency_key: str, *, field_confidences: dict[str, str] | None = None, source_evidence_id: UUID | None = None, model_name: str | None = None) -> ConfirmationRecord: ...


class RecordWorkflow:
    def __init__(self, *, confirmation_workflow: CandidateConfirmationWorkflow, extraction_provider: ExtractionProvider, asr_provider: ASRProvider, evidence_service: EvidenceService | None = None, customer_service: CustomerService | None = None) -> None:
        self.confirmation_workflow = confirmation_workflow
        self.extraction_provider = extraction_provider
        self.asr_provider = asr_provider
        self.evidence_service = evidence_service
        self.customer_service = customer_service

    async def from_text(self, shop_id: UUID, text: str, idempotency_key: str, *, source_evidence_id: UUID | None = None) -> ConfirmationRecord:
        try:
            extraction = await self.extraction_provider.extract(text)
            draft = record_draft_adapter.validate_python(extraction.draft)
            canonical_json = draft.model_dump(mode="json")
            confidences = certain_field_confidences(canonical_json)
            confidences.update({field: self._confidence_as_string(value) for field, value in extraction.field_confidences.items()})
        except ProviderUnavailable:
            raise
        except (AttributeError, InvalidOperation, TypeError, ValidationError, ValueError) as error:
            raise ProviderUnavailable("extraction provider returned an invalid candidate") from error
        draft = await self._with_customer_match(shop_id, draft)
        return await self.confirmation_workflow.create(shop_id, draft, idempotency_key, field_confidences=confidences, source_evidence_id=source_evidence_id, model_name=extraction.model_name)

    async def from_voice(self, shop_id: UUID, audio: bytes, mime_type: str, original_filename: str | None, idempotency_key: str) -> ConfirmationRecord:
        if self.evidence_service is None:
            raise RuntimeError("voice recording requires an evidence service")

        async def create_candidate() -> ConfirmationRecord:
            evidence = await self.evidence_service.create_upload(shop_id=shop_id, original_filename=original_filename, mime_type=mime_type, data=audio)
            try:
                transcript = await self.asr_provider.transcribe(audio, evidence.mime_type)
                transcript_text = transcript.transcript
            except ProviderUnavailable:
                raise
            except (AttributeError, TypeError, ValueError) as error:
                raise ProviderUnavailable("ASR provider returned an invalid transcript") from error
            await self.evidence_service.attach_transcript(shop_id, evidence.id, transcript_text)
            return await self.from_text(shop_id, transcript_text, idempotency_key, source_evidence_id=evidence.id)

        reserve = getattr(self.confirmation_workflow, "run_creation_once", None)
        if reserve is None:
            return await create_candidate()
        return await reserve(shop_id, idempotency_key, create_candidate)

    async def _with_customer_match(self, shop_id: UUID, draft: RecordDraft) -> RecordDraft:
        if self.customer_service is None or not hasattr(draft, "items"):
            return draft
        matched = await self.customer_service.match(shop_id, draft.customer_name)
        if matched.customer_id is None:
            return draft
        payload = draft.model_dump(mode="python")
        payload["customer_id"] = matched.customer_id
        return record_draft_adapter.validate_python(payload)

    @staticmethod
    def _confidence_as_string(confidence: Decimal) -> str:
        normalized = Decimal(str(confidence))
        if not normalized.is_finite() or not Decimal("0") <= normalized <= Decimal("1"):
            raise ValueError("confidence must be between zero and one")
        return f"{normalized:.2f}"
