from decimal import Decimal

import pytest
from pydantic import ValidationError

from xiaodianji.schemas.record import PaymentDraft, QuoteDraft, TransactionDraft


def test_transaction_draft_recalculates_two_item_total() -> None:
    draft = TransactionDraft.model_validate(
        {
            "target_type": "transaction",
            "customer_name": "王老板",
            "occurred_at": "2026-07-27T10:00:00+08:00",
            "payment_status": "unpaid",
            "items": [
                {
                    "product": "插座",
                    "quantity": "10",
                    "unit": "个",
                    "unit_price": "12.00",
                },
                {
                    "product": "电线",
                    "quantity": "2",
                    "unit": "卷",
                    "unit_price": "150.00",
                },
            ],
        }
    )

    assert draft.items[0].subtotal == Decimal("120.00")
    assert draft.items[1].subtotal == Decimal("300.00")
    assert draft.total_amount == Decimal("420.00")


def test_quote_draft_uses_the_same_line_item_calculation() -> None:
    draft = QuoteDraft.model_validate(
        {
            "target_type": "quote",
            "customer_name": "王老板",
            "quoted_at": "2026-07-27T10:00:00+08:00",
            "items": [
                {
                    "product": "角磨机",
                    "quantity": "3",
                    "unit": "台",
                    "unit_price": "199.90",
                }
            ],
        }
    )

    assert draft.items[0].subtotal == Decimal("599.70")
    assert draft.total_amount == Decimal("599.70")


def test_transaction_requires_at_least_one_item() -> None:
    with pytest.raises(ValidationError):
        TransactionDraft.model_validate(
            {
                "target_type": "transaction",
                "customer_name": "王老板",
                "occurred_at": "2026-07-27T10:00:00+08:00",
                "payment_status": "unpaid",
                "items": [],
            }
        )


def test_payment_amount_is_quantized_to_cents() -> None:
    draft = PaymentDraft.model_validate(
        {
            "target_type": "payment",
            "customer_name": "王老板",
            "paid_at": "2026-07-27T10:00:00+08:00",
            "amount": "200",
        }
    )

    assert str(draft.amount) == "200.00"


def test_negative_money_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PaymentDraft.model_validate(
            {
                "target_type": "payment",
                "customer_name": "王老板",
                "paid_at": "2026-07-27T10:00:00+08:00",
                "amount": "-1",
            }
        )

