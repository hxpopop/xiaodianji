from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class RecordCreationReservation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "record_creation_reservations"
    __table_args__ = (UniqueConstraint("shop_id", "idempotency_key", name="uq_record_reservation_shop_idempotency"),)

    shop_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
