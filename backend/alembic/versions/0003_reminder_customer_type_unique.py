"""Enforce one reminder per shop, customer, and type.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_NAME = "uq_reminder_shop_customer_type"


def _has_constraint(bind) -> bool:
    return CONSTRAINT_NAME in {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints("reminders")
    }


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_constraint(bind):
        op.create_unique_constraint(
            CONSTRAINT_NAME,
            "reminders",
            ["shop_id", "customer_id", "type"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_constraint(bind):
        op.drop_constraint(CONSTRAINT_NAME, "reminders", type_="unique")
