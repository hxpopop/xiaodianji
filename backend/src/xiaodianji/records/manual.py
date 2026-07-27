from typing import Protocol
from uuid import UUID, uuid4

from xiaodianji.confirmations.service import (
    ConfirmationEventRecord,
    ConfirmationRecord,
)
from xiaodianji.models import ConfirmationStatus
from xiaodianji.schemas.record import RecordDraft


class ManualConfirmationRepository(Protocol):
    async def find_by_creation_key(
        self,
        shop_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord | None: ...

    async def add(self, record: ConfirmationRecord) -> ConfirmationRecord: ...

    async def add_event(
        self,
        event: ConfirmationEventRecord,
    ) -> ConfirmationEventRecord: ...


def certain_field_confidences(payload: object, prefix: str = "") -> dict[str, str]:
    confidences: dict[str, str] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            confidences.update(certain_field_confidences(value, path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}.{index}" if prefix else str(index)
            confidences.update(certain_field_confidences(value, path))
    elif prefix:
        confidences[prefix] = "1.00"
    return confidences


class ManualRecordService:
    def __init__(self, repository: ManualConfirmationRepository) -> None:
        self.repository = repository

    async def create(
        self,
        shop_id: UUID,
        draft: RecordDraft,
        idempotency_key: str,
    ) -> ConfirmationRecord:
        existing = await self.repository.find_by_creation_key(
            shop_id,
            idempotency_key,
        )
        if existing is not None:
            return existing

        extracted_json = draft.model_dump(mode="json")
        record = ConfirmationRecord(
            id=uuid4(),
            shop_id=shop_id,
            target_type=draft.target_type,
            extracted_json=extracted_json,
            edited_json=None,
            field_confidences=certain_field_confidences(extracted_json),
            status=ConfirmationStatus.PENDING,
            creation_idempotency_key=idempotency_key,
        )
        await self.repository.add(record)
        await self.repository.add_event(
            ConfirmationEventRecord(
                confirmation_id=record.id,
                event_type="created",
                before_json=None,
                after_json=extracted_json,
            )
        )
        return record

