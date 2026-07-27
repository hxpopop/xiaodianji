from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ReminderStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class Reminder(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "customer_id",
            "type",
            name="uq_reminder_shop_customer_type",
        ),
    )

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, native_enum=False, length=20),
        default=ReminderStatus.OPEN,
        nullable=False,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Anomaly(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "anomalies"

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, native_enum=False, length=20),
        default=ReminderStatus.OPEN,
        nullable=False,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
