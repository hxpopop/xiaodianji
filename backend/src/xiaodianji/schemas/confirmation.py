from uuid import UUID

from pydantic import BaseModel

from xiaodianji.confirmations.service import ConfirmationRecord
from xiaodianji.models import ConfirmationStatus


class ConfirmationRead(BaseModel):
    id: UUID
    shop_id: UUID
    target_type: str
    status: ConfirmationStatus
    effective_json: dict
    field_confidences: dict[str, str]
    formal_record_type: str | None
    formal_record_id: UUID | None

    @classmethod
    def from_record(cls, record: ConfirmationRecord) -> "ConfirmationRead":
        return cls(
            id=record.id,
            shop_id=record.shop_id,
            target_type=record.target_type,
            status=record.status,
            effective_json=record.effective_json,
            field_confidences=record.field_confidences,
            formal_record_type=record.formal_record_type,
            formal_record_id=record.formal_record_id,
        )

