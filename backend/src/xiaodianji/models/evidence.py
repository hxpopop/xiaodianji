from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class EvidenceType(StrEnum):
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"


class EvidenceStatus(StrEnum):
    READY = "ready"
    PROCESSING = "processing"
    FAILED = "failed"


class Evidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "evidences"
    __table_args__ = (
        UniqueConstraint("shop_id", "object_key", name="uq_evidence_shop_object"),
    )

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, native_enum=False, length=20),
        nullable=False,
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, native_enum=False, length=20),
        default=EvidenceStatus.READY,
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    asr_text: Mapped[str | None] = mapped_column(Text)

