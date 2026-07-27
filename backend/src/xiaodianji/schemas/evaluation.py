from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from pydantic import BaseModel, Field


RATE_SCALE = Decimal("0.0001")


def four_places(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("0.0000")
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        RATE_SCALE, rounding=ROUND_HALF_UP
    )


class Score(BaseModel):
    correct: int = Field(ge=0)
    total: int = Field(ge=0)
    accuracy: Decimal

    @classmethod
    def from_counts(cls, correct: int, total: int) -> "Score":
        return cls(correct=correct, total=total, accuracy=four_places(correct, total))


class FieldScores(BaseModel):
    customer: Score
    products: Score
    quantities: Score
    amounts: Score
    payment_status: Score


class EvaluationMetrics(FieldScores):
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(default=0, ge=0)
    average_latency_ms: Decimal = Decimal("0.0000")


class ConfirmationRate(BaseModel):
    count: int = Field(ge=0)
    total: int = Field(ge=0)
    rate: Decimal

    @classmethod
    def from_counts(cls, count: int, total: int) -> "ConfirmationRate":
        return cls(count=count, total=total, rate=four_places(count, total))


class ConfirmationRates(BaseModel):
    direct: ConfirmationRate
    edited: ConfirmationRate
    cancelled: ConfirmationRate
    total: int = Field(ge=0)


class EvaluationResultRead(BaseModel):
    case_id: UUID
    stable_key: str
    predicted_json: dict
    field_scores: FieldScores
    latency_ms: int


class EvaluationRunRead(BaseModel):
    id: UUID
    shop_id: UUID
    model_name: str
    started_at: str
    finished_at: str | None
    metrics: EvaluationMetrics
    confirmation_rates: ConfirmationRates
    case_count: int
    failed_case_count: int
    average_latency_ms: Decimal
    results: list[EvaluationResultRead] = []


class EvaluationRunRequest(BaseModel):
    model_name: str = Field(default="configured", min_length=1, max_length=120)
