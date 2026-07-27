"""Add durable record creation reservations.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("record_creation_reservations"):
        return
    op.create_table(
        "record_creation_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "idempotency_key", name="uq_record_reservation_shop_idempotency"),
    )
    op.create_index("ix_record_creation_reservations_shop_id", "record_creation_reservations", ["shop_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("record_creation_reservations"):
        op.drop_table("record_creation_reservations")
