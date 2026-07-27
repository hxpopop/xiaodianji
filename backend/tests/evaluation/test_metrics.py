from decimal import Decimal

from xiaodianji.evaluation.metrics import (
    aggregate_scores,
    confirmation_rates,
    score_case,
)


def transaction(*, products: list[str], quantities: list[str], prices: list[str]):
    return {
        "target_type": "transaction",
        "customer_name": "星河装饰",
        "occurred_at": "2026-07-27T10:00:00+08:00",
        "payment_status": "unpaid",
        "items": [
            {
                "product": product,
                "quantity": quantity,
                "unit": "件",
                "unit_price": price,
            }
            for product, quantity, price in zip(products, quantities, prices, strict=True)
        ],
    }


def test_score_case_reports_hand_checked_core_field_numerators_and_denominators() -> None:
    expected = transaction(
        products=["水管", "弯头"], quantities=["2", "3"], prices=["12.50", "3.20"]
    )
    predicted = transaction(
        products=["水管", "直通"], quantities=["2.000", "3.0"], prices=["12.5", "3.20"]
    )

    scores = score_case(expected, predicted)

    assert scores.customer.model_dump() == {"correct": 1, "total": 1, "accuracy": Decimal("1.0000")}
    assert scores.products.model_dump() == {"correct": 1, "total": 2, "accuracy": Decimal("0.5000")}
    assert scores.quantities.model_dump() == {"correct": 2, "total": 2, "accuracy": Decimal("1.0000")}
    assert scores.amounts.model_dump() == {"correct": 2, "total": 2, "accuracy": Decimal("1.0000")}
    assert scores.payment_status.model_dump() == {"correct": 1, "total": 1, "accuracy": Decimal("1.0000")}


def test_score_case_counts_missing_products_as_incorrect_without_float_comparisons() -> None:
    expected = transaction(
        products=["水管", "弯头"], quantities=["2", "3"], prices=["12.50", "3.20"]
    )
    predicted = transaction(products=["水管"], quantities=["2"], prices=["12.50"])

    scores = score_case(expected, predicted)

    assert scores.products.model_dump() == {"correct": 1, "total": 2, "accuracy": Decimal("0.5000")}
    assert scores.quantities.model_dump() == {"correct": 1, "total": 2, "accuracy": Decimal("0.5000")}
    assert scores.amounts.model_dump() == {"correct": 1, "total": 2, "accuracy": Decimal("0.5000")}


def test_score_case_excludes_payment_status_for_non_transaction_records() -> None:
    expected = {
        "target_type": "payment",
        "customer_name": "星河装饰",
        "paid_at": "2026-07-27T10:00:00+08:00",
        "amount": "100.00",
    }

    scores = score_case(expected, expected)

    assert scores.payment_status.model_dump() == {"correct": 0, "total": 0, "accuracy": Decimal("0.0000")}
    assert scores.amounts.model_dump() == {"correct": 1, "total": 1, "accuracy": Decimal("1.0000")}


def test_aggregate_scores_and_confirmation_rates_return_four_decimal_rates() -> None:
    aggregate = aggregate_scores(
        [
            score_case(
                transaction(products=["水管"], quantities=["2"], prices=["12.50"]),
                transaction(products=["水管"], quantities=["2"], prices=["12.50"]),
            ),
            score_case(
                transaction(products=["弯头"], quantities=["3"], prices=["3.20"]),
                transaction(products=["直通"], quantities=["3"], prices=["3.20"]),
            ),
        ]
    )

    rates = confirmation_rates(direct=6, edited=3, cancelled=1)
    empty = confirmation_rates(direct=0, edited=0, cancelled=0)

    assert aggregate.products.model_dump() == {"correct": 1, "total": 2, "accuracy": Decimal("0.5000")}
    assert aggregate.case_count == 2
    assert rates.model_dump() == {
        "direct": {"count": 6, "total": 10, "rate": Decimal("0.6000")},
        "edited": {"count": 3, "total": 10, "rate": Decimal("0.3000")},
        "cancelled": {"count": 1, "total": 10, "rate": Decimal("0.1000")},
        "total": 10,
    }
    assert empty.direct.rate == Decimal("0.0000")
