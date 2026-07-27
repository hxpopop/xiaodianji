from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from xiaodianji.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class EvaluationCase(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint("shop_id", "stable_key", name="uq_evaluation_case_shop_stable_key"),
    )

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False)
    input_type: Mapped[str] = mapped_column(String(32), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)


class EvaluationRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "evaluation_runs"

    shop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class EvaluationResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "evaluation_results"

    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicted_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    field_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
