from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


CENT = Decimal("0.01")


@dataclass(frozen=True)
class AnomalyFinding:
    type: Literal["amount_mismatch", "duplicate_idempotency"]
    message: str
    details: dict[str, Decimal]


def validate_amounts(
    item_subtotals: list[Decimal], stated_total: Decimal
) -> AnomalyFinding | None:
    calculated_total = sum(item_subtotals, Decimal()).quantize(CENT)
    stated = stated_total.quantize(CENT)
    difference = (calculated_total - stated).quantize(CENT)
    if difference == Decimal():
        return None
    return AnomalyFinding(
        type="amount_mismatch",
        message="金额不一致",
        details={
            "calculated_total": calculated_total,
            "stated_total": stated,
            "difference": difference,
        },
    )


def duplicate_idempotency_finding() -> AnomalyFinding:
    return AnomalyFinding(
        type="duplicate_idempotency",
        message="重复提交异常",
        details={},
    )
