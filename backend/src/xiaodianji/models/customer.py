from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "customers"

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(String(500))

    aliases: Mapped[list["CustomerAlias"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class CustomerAlias(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "customer_aliases"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "normalized_alias",
            name="uq_customer_alias_shop_normalized",
        ),
    )

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(120), nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="aliases")

