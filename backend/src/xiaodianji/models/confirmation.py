from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CONFIRMED_AFTER_EDIT = "confirmed_after_edit"
    CANCELLED = "cancelled"


class ConfirmationTargetType(StrEnum):
    QUOTE = "quote"
    TRANSACTION = "transaction"
    PAYMENT = "payment"


class ConfirmationEventType(StrEnum):
    CREATED = "created"
    EDITED = "edited"
    CONFIRMED = "confirmed"
    CONFIRMED_AFTER_EDIT = "confirmed_after_edit"
    CANCELLED = "cancelled"


class PendingConfirmation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "pending_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "idempotency_key",
            name="uq_confirmation_shop_idempotency",
        ),
    )

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[ConfirmationTargetType] = mapped_column(
        Enum(ConfirmationTargetType, native_enum=False, length=24),
        nullable=False,
    )
    source_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidences.id", ondelete="SET NULL"),
    )
    extracted_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edited_json: Mapped[dict | None] = mapped_column(JSONB)
    field_confidences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[ConfirmationStatus] = mapped_column(
        Enum(ConfirmationStatus, native_enum=False, length=32),
        default=ConfirmationStatus.PENDING,
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120))
    formal_record_type: Mapped[str | None] = mapped_column(String(32))
    formal_record_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    events: Mapped[list["ConfirmationEvent"]] = relationship(
        back_populates="confirmation",
        cascade="all, delete-orphan",
    )


class ConfirmationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "confirmation_events"

    confirmation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pending_confirmations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[ConfirmationEventType] = mapped_column(
        Enum(ConfirmationEventType, native_enum=False, length=32),
        nullable=False,
    )
    before_json: Mapped[dict | None] = mapped_column(JSONB)
    after_json: Mapped[dict | None] = mapped_column(JSONB)

    confirmation: Mapped[PendingConfirmation] = relationship(back_populates="events")

