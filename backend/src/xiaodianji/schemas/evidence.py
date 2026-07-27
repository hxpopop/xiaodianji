from uuid import UUID

from pydantic import BaseModel

from xiaodianji.evidences.service import EvidenceRecord
from xiaodianji.models import EvidenceStatus, EvidenceType


class EvidenceRead(BaseModel):
    id: UUID
    type: EvidenceType
    status: EvidenceStatus
    original_filename: str | None
    mime_type: str
    size_bytes: int
    asr_text: str | None
    access_url: str | None

    @classmethod
    def from_record(cls, record: EvidenceRecord) -> "EvidenceRead":
        return cls(
            id=record.id,
            type=record.type,
            status=record.status,
            original_filename=record.original_filename,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            asr_text=record.asr_text,
            access_url=record.access_url,
        )

