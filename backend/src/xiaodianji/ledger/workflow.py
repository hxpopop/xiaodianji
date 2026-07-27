from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.confirmations.service import (
    ConfirmationConflict,
    ConfirmationNotFound,
    ConfirmationRecord,
)
from xiaodianji.ledger.balance import BalanceService
from xiaodianji.ledger.service import LedgerService
from xiaodianji.models import (
    ConfirmationEvent,
    ConfirmationEventType,
    ConfirmationStatus,
    ConfirmationTargetType,
    PendingConfirmation,
)
from xiaodianji.records.manual import certain_field_confidences
from xiaodianji.schemas.record import RecordDraft, record_draft_adapter


class SQLAlchemyLedgerWorkflow:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        ledger_service: LedgerService | None = None,
        balance_service: BalanceService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.ledger_service = ledger_service or LedgerService()
        self.balance_service = balance_service or BalanceService(session_factory)

    async def create(
        self,
        shop_id: UUID,
        draft: RecordDraft,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        extracted_json = draft.model_dump(mode="json")
        confirmation_id = uuid4()
        statement = (
            insert(PendingConfirmation)
            .values(
                id=confirmation_id,
                shop_id=shop_id,
                target_type=ConfirmationTargetType(draft.target_type),
                extracted_json=extracted_json,
                edited_json=None,
                field_confidences=certain_field_confidences(extracted_json),
                status=ConfirmationStatus.PENDING,
                idempotency_key=idempotency_key,
                schema_version="1",
            )
            .on_conflict_do_nothing(
                constraint="uq_confirmation_shop_idempotency"
            )
            .returning(PendingConfirmation.id)
        )
        async with self.session_factory.begin() as session:
            inserted_id = await session.scalar(statement)
            if inserted_id is not None:
                session.add(
                    ConfirmationEvent(
                        confirmation_id=inserted_id,
                        event_type=ConfirmationEventType.CREATED,
                        before_json=None,
                        after_json=extracted_json,
                    )
                )
                await session.flush()
                confirmation = await session.get(
                    PendingConfirmation,
                    inserted_id,
                )
            else:
                confirmation = await session.scalar(
                    select(PendingConfirmation).where(
                        PendingConfirmation.shop_id == shop_id,
                        PendingConfirmation.idempotency_key == idempotency_key,
                    )
                )
            if confirmation is None:
                raise RuntimeError("idempotent confirmation could not be loaded")
            result = self._to_record(confirmation)
        return result

    async def get(self, confirmation_id: UUID) -> ConfirmationRecord:
        async with self.session_factory() as session:
            confirmation = await session.get(PendingConfirmation, confirmation_id)
            if confirmation is None:
                raise ConfirmationNotFound(str(confirmation_id))
            return self._to_record(confirmation)

    async def update_draft(
        self,
        confirmation_id: UUID,
        edited_json: dict,
    ) -> ConfirmationRecord:
        async with self.session_factory.begin() as session:
            confirmation = await self._required_locked(session, confirmation_id)
            if confirmation.status is not ConfirmationStatus.PENDING:
                raise ConfirmationConflict("only pending confirmations can be edited")
            before_json = confirmation.edited_json or confirmation.extracted_json
            validated = record_draft_adapter.validate_python(edited_json)
            after_json = validated.model_dump(mode="json")
            confirmation.edited_json = after_json
            session.add(
                ConfirmationEvent(
                    confirmation_id=confirmation.id,
                    event_type=ConfirmationEventType.EDITED,
                    before_json=before_json,
                    after_json=after_json,
                )
            )
            await session.flush()
            result = self._to_record(confirmation)
        return result

    async def confirm(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        async with self.session_factory.begin() as session:
            confirmation = await self._required_locked(session, confirmation_id)
            if confirmation.status in {
                ConfirmationStatus.CONFIRMED,
                ConfirmationStatus.CONFIRMED_AFTER_EDIT,
            }:
                if confirmation.resolution_idempotency_key == idempotency_key:
                    return self._to_record(confirmation)
                raise ConfirmationConflict("confirmation is already resolved")
            if confirmation.status is not ConfirmationStatus.PENDING:
                raise ConfirmationConflict(
                    "cancelled confirmation cannot be confirmed"
                )

            effective_json = (
                confirmation.edited_json or confirmation.extracted_json
            )
            draft = record_draft_adapter.validate_python(effective_json)
            canonical_json = draft.model_dump(mode="json")
            if confirmation.edited_json is not None:
                confirmation.edited_json = canonical_json
                final_status = ConfirmationStatus.CONFIRMED_AFTER_EDIT
                event_type = ConfirmationEventType.CONFIRMED_AFTER_EDIT
            else:
                confirmation.extracted_json = canonical_json
                final_status = ConfirmationStatus.CONFIRMED
                event_type = ConfirmationEventType.CONFIRMED

            formal_record = await self.ledger_service.create_from_confirmation(
                session,
                confirmation,
                draft,
            )
            confirmation.formal_record_type = formal_record.record_type
            confirmation.formal_record_id = formal_record.record_id
            confirmation.resolution_idempotency_key = idempotency_key
            confirmation.resolved_at = datetime.now(timezone.utc)
            confirmation.status = final_status
            session.add(
                ConfirmationEvent(
                    confirmation_id=confirmation.id,
                    event_type=event_type,
                    before_json=canonical_json,
                    after_json=canonical_json,
                )
            )
            await session.flush()
            result = self._to_record(confirmation)
        return result

    async def cancel(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        async with self.session_factory.begin() as session:
            confirmation = await self._required_locked(session, confirmation_id)
            if confirmation.status is ConfirmationStatus.CANCELLED:
                if confirmation.resolution_idempotency_key == idempotency_key:
                    return self._to_record(confirmation)
                raise ConfirmationConflict("confirmation is already cancelled")
            if confirmation.status is not ConfirmationStatus.PENDING:
                raise ConfirmationConflict(
                    "confirmed record cannot be cancelled"
                )

            effective_json = (
                confirmation.edited_json or confirmation.extracted_json
            )
            confirmation.status = ConfirmationStatus.CANCELLED
            confirmation.resolution_idempotency_key = idempotency_key
            confirmation.resolved_at = datetime.now(timezone.utc)
            session.add(
                ConfirmationEvent(
                    confirmation_id=confirmation.id,
                    event_type=ConfirmationEventType.CANCELLED,
                    before_json=effective_json,
                    after_json=None,
                )
            )
            await session.flush()
            result = self._to_record(confirmation)
        return result

    async def customer_balance(
        self,
        shop_id: UUID,
        customer_id: UUID,
    ) -> Decimal:
        return await self.balance_service.customer_balance(shop_id, customer_id)

    async def _required_locked(
        self,
        session: AsyncSession,
        confirmation_id: UUID,
    ) -> PendingConfirmation:
        confirmation = await session.scalar(
            select(PendingConfirmation)
            .where(PendingConfirmation.id == confirmation_id)
            .with_for_update()
        )
        if confirmation is None:
            raise ConfirmationNotFound(str(confirmation_id))
        return confirmation

    @staticmethod
    def _to_record(confirmation: PendingConfirmation) -> ConfirmationRecord:
        return ConfirmationRecord(
            id=confirmation.id,
            shop_id=confirmation.shop_id,
            target_type=confirmation.target_type.value,
            extracted_json=confirmation.extracted_json,
            edited_json=confirmation.edited_json,
            field_confidences=confirmation.field_confidences,
            status=confirmation.status,
            creation_idempotency_key=confirmation.idempotency_key,
            resolution_idempotency_key=confirmation.resolution_idempotency_key,
            formal_record_type=confirmation.formal_record_type,
            formal_record_id=confirmation.formal_record_id,
            resolved_at=confirmation.resolved_at,
            events=[],
        )

