from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from xiaodianji.models import ConfirmationStatus
from xiaodianji.schemas.record import record_draft_adapter


class ConfirmationConflict(RuntimeError):
    pass


class ConfirmationNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class FormalRecordRef:
    record_type: str
    record_id: UUID


@dataclass(slots=True)
class ConfirmationEventRecord:
    confirmation_id: UUID
    event_type: str
    before_json: dict | None
    after_json: dict | None


@dataclass(slots=True)
class ConfirmationRecord:
    id: UUID
    shop_id: UUID
    target_type: str
    extracted_json: dict
    edited_json: dict | None
    field_confidences: dict[str, str]
    status: ConfirmationStatus
    creation_idempotency_key: str
    resolution_idempotency_key: str | None = None
    formal_record_type: str | None = None
    formal_record_id: UUID | None = None
    resolved_at: datetime | None = None
    events: list[ConfirmationEventRecord] = field(default_factory=list)

    @property
    def effective_json(self) -> dict:
        return self.edited_json or self.extracted_json


class ConfirmationRepository(Protocol):
    async def get(self, confirmation_id: UUID) -> ConfirmationRecord | None: ...
    async def save(self, record: ConfirmationRecord) -> ConfirmationRecord: ...
    async def add_event(
        self,
        event: ConfirmationEventRecord,
    ) -> ConfirmationEventRecord: ...


class FormalRecordWriter(Protocol):
    async def write(self, record: ConfirmationRecord) -> FormalRecordRef: ...


class ConfirmationService:
    def __init__(
        self,
        repository: ConfirmationRepository,
        writer: FormalRecordWriter,
    ) -> None:
        self.repository = repository
        self.writer = writer

    async def get(self, confirmation_id: UUID) -> ConfirmationRecord:
        return await self._required(confirmation_id)

    async def update_draft(
        self,
        confirmation_id: UUID,
        edited_json: dict,
    ) -> ConfirmationRecord:
        record = await self._required_pending(confirmation_id)
        before_json = record.effective_json
        validated_draft = record_draft_adapter.validate_python(edited_json)
        after_json = validated_draft.model_dump(mode="json")
        record.edited_json = after_json
        await self.repository.save(record)
        await self.repository.add_event(
            ConfirmationEventRecord(
                confirmation_id=record.id,
                event_type="edited",
                before_json=before_json,
                after_json=after_json,
            )
        )
        return record

    async def confirm(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        record = await self._required(confirmation_id)
        if record.status in {
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.CONFIRMED_AFTER_EDIT,
        }:
            if record.resolution_idempotency_key == idempotency_key:
                return record
            raise ConfirmationConflict("confirmation is already resolved")
        if record.status is not ConfirmationStatus.PENDING:
            raise ConfirmationConflict("cancelled confirmation cannot be confirmed")

        validated_draft = record_draft_adapter.validate_python(record.effective_json)
        if record.edited_json is not None:
            record.edited_json = validated_draft.model_dump(mode="json")
        else:
            record.extracted_json = validated_draft.model_dump(mode="json")

        formal_record = await self.writer.write(record)
        record.formal_record_type = formal_record.record_type
        record.formal_record_id = formal_record.record_id
        record.resolution_idempotency_key = idempotency_key
        record.resolved_at = datetime.now(timezone.utc)
        record.status = (
            ConfirmationStatus.CONFIRMED_AFTER_EDIT
            if record.edited_json is not None
            else ConfirmationStatus.CONFIRMED
        )
        await self.repository.save(record)
        await self.repository.add_event(
            ConfirmationEventRecord(
                confirmation_id=record.id,
                event_type=record.status.value,
                before_json=record.effective_json,
                after_json=record.effective_json,
            )
        )
        return record

    async def cancel(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        record = await self._required(confirmation_id)
        if record.status is ConfirmationStatus.CANCELLED:
            if record.resolution_idempotency_key == idempotency_key:
                return record
            raise ConfirmationConflict("confirmation is already cancelled")
        if record.status is not ConfirmationStatus.PENDING:
            raise ConfirmationConflict("confirmed record cannot be cancelled")

        record.status = ConfirmationStatus.CANCELLED
        record.resolution_idempotency_key = idempotency_key
        record.resolved_at = datetime.now(timezone.utc)
        await self.repository.save(record)
        await self.repository.add_event(
            ConfirmationEventRecord(
                confirmation_id=record.id,
                event_type="cancelled",
                before_json=record.effective_json,
                after_json=None,
            )
        )
        return record

    async def _required(self, confirmation_id: UUID) -> ConfirmationRecord:
        record = await self.repository.get(confirmation_id)
        if record is None:
            raise ConfirmationNotFound(str(confirmation_id))
        return record

    async def _required_pending(self, confirmation_id: UUID) -> ConfirmationRecord:
        record = await self._required(confirmation_id)
        if record.status is not ConfirmationStatus.PENDING:
            raise ConfirmationConflict("only pending confirmations can be edited")
        return record
