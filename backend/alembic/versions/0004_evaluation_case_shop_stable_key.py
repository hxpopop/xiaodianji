"""Scope fixed evaluation case keys to a shop.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "evaluation_cases"
COMPOSITE_NAME = "uq_evaluation_case_shop_stable_key"


def _unique_constraints(bind) -> list[dict]:
    return sa.inspect(bind).get_unique_constraints(TABLE)


def _constraint_names(bind, columns: list[str]) -> list[str]:
    return [
        constraint["name"]
        for constraint in _unique_constraints(bind)
        if constraint["name"] and constraint.get("column_names") == columns
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for name in _constraint_names(bind, ["stable_key"]):
        op.drop_constraint(name, TABLE, type_="unique")
    if not _constraint_names(bind, ["shop_id", "stable_key"]):
        op.create_unique_constraint(
            COMPOSITE_NAME, TABLE, ["shop_id", "stable_key"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    for name in _constraint_names(bind, ["shop_id", "stable_key"]):
        op.drop_constraint(name, TABLE, type_="unique")
    if not _constraint_names(bind, ["stable_key"]):
        op.create_unique_constraint(None, TABLE, ["stable_key"])
