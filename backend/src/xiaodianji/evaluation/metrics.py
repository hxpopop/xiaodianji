from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable

from xiaodianji.schemas.evaluation import (
    ConfirmationRate,
    ConfirmationRates,
    EvaluationMetrics,
    FieldScores,
    Score,
)


CENT = Decimal("0.01")
CORE_FIELDS = (
    "customer",
    "products",
    "quantities",
    "amounts",
    "payment_status",
)


def _decimal_equal(
    left: Any,
    right: Any,
    *,
    scale: Decimal = CENT,
) -> bool:
    try:
        return Decimal(str(left)).quantize(
            scale,
            rounding=ROUND_HALF_UP,
        ) == Decimal(str(right)).quantize(
            scale,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        return False


def _quantity_equal(left: Any, right: Any) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, TypeError, ValueError):
        return False


def _text_equal(left: Any, right: Any) -> bool:
    return (
        isinstance(left, str)
        and isinstance(right, str)
        and left.strip() == right.strip()
    )


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def _position_score(
    expected: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    key: str,
    comparator: Callable[[Any, Any], bool],
) -> Score:
    correct = sum(
        comparator(item.get(key), predicted[index].get(key))
        for index, item in enumerate(expected)
        if index < len(predicted)
    )
    return Score.from_counts(correct, len(expected))


def _record_total(
    payload: dict[str, Any],
    items: list[dict[str, Any]],
) -> Decimal | Any:
    if "total_amount" in payload:
        return payload["total_amount"]
    try:
        subtotals = (
            (
                Decimal(str(item["quantity"]))
                * Decimal(str(item["unit_price"]))
            ).quantize(CENT, rounding=ROUND_HALF_UP)
            for item in items
        )
        return sum(subtotals, start=Decimal("0")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return None


def score_case(
    expected: dict[str, Any],
    predicted: dict[str, Any],
) -> FieldScores:
    """Score expected core fields with the production rounding rules."""
    expected_items = _items(expected)
    predicted_items = _items(predicted)
    expected_customer = expected.get("customer_id") or expected.get(
        "customer_name"
    )
    predicted_customer = predicted.get("customer_id") or predicted.get(
        "customer_name"
    )
    customer = Score.from_counts(
        int(_text_equal(expected_customer, predicted_customer)),
        1,
    )
    if expected.get("target_type") == "payment":
        amounts = Score.from_counts(
            int(
                _decimal_equal(
                    expected.get("amount"),
                    predicted.get("amount"),
                )
            ),
            1,
        )
        products = quantities = Score.from_counts(0, 0)
    else:
        products = _position_score(
            expected_items,
            predicted_items,
            "product",
            _text_equal,
        )
        quantities = _position_score(
            expected_items,
            predicted_items,
            "quantity",
            _quantity_equal,
        )
        unit_prices = _position_score(
            expected_items,
            predicted_items,
            "unit_price",
            _decimal_equal,
        )
        total_is_correct = _decimal_equal(
            _record_total(expected, expected_items),
            predicted.get("total_amount"),
        )
        amounts = Score.from_counts(
            unit_prices.correct + int(total_is_correct),
            unit_prices.total + 1,
        )
    payment_status = Score.from_counts(
        int(
            _text_equal(
                expected.get("payment_status"),
                predicted.get("payment_status"),
            )
        ),
        1 if expected.get("target_type") == "transaction" else 0,
    )
    return FieldScores(
        customer=customer,
        products=products,
        quantities=quantities,
        amounts=amounts,
        payment_status=payment_status,
    )


def aggregate_scores(scores: list[FieldScores]) -> EvaluationMetrics:
    totals: dict[str, Score] = {}
    for field in CORE_FIELDS:
        correct = sum(getattr(score, field).correct for score in scores)
        total = sum(getattr(score, field).total for score in scores)
        totals[field] = Score.from_counts(correct, total)
    return EvaluationMetrics(**totals, case_count=len(scores))


def confirmation_rates(
    *,
    direct: int,
    edited: int,
    cancelled: int,
) -> ConfirmationRates:
    total = direct + edited + cancelled
    return ConfirmationRates(
        direct=ConfirmationRate.from_counts(direct, total),
        edited=ConfirmationRate.from_counts(edited, total),
        cancelled=ConfirmationRate.from_counts(cancelled, total),
        total=total,
    )
