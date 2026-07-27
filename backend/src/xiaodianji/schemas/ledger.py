from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_serializer

from xiaodianji.models import PaymentStatus, Quote, Transaction


def money_string(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


class LedgerItemRead(BaseModel):
    id: UUID
    product: str
    spec: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal

    @field_serializer("unit_price", "subtotal")
    def serialize_money(self, value: Decimal) -> str:
        return money_string(value)


class TransactionRead(BaseModel):
    id: UUID
    customer_id: UUID
    occurred_at: datetime
    payment_status: PaymentStatus
    total_amount: Decimal
    source_evidence_id: UUID | None
    items: list[LedgerItemRead]

    @field_serializer("total_amount")
    def serialize_total(self, value: Decimal) -> str:
        return money_string(value)

    @classmethod
    def from_model(cls, transaction: Transaction) -> "TransactionRead":
        return cls(
            id=transaction.id,
            customer_id=transaction.customer_id,
            occurred_at=transaction.occurred_at,
            payment_status=transaction.payment_status,
            total_amount=transaction.total_amount,
            source_evidence_id=transaction.source_evidence_id,
            items=[
                LedgerItemRead(
                    id=item.id,
                    product=item.product,
                    spec=item.spec,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for item in transaction.items
            ],
        )


class QuoteRead(BaseModel):
    id: UUID
    customer_id: UUID
    quoted_at: datetime
    total_amount: Decimal
    source_evidence_id: UUID | None
    items: list[LedgerItemRead]

    @field_serializer("total_amount")
    def serialize_total(self, value: Decimal) -> str:
        return money_string(value)

    @classmethod
    def from_model(cls, quote: Quote) -> "QuoteRead":
        return cls(
            id=quote.id,
            customer_id=quote.customer_id,
            quoted_at=quote.quoted_at,
            total_amount=quote.total_amount,
            source_evidence_id=quote.source_evidence_id,
            items=[
                LedgerItemRead(
                    id=item.id,
                    product=item.product,
                    spec=item.spec,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for item in quote.items
            ],
        )


class CustomerBalanceRead(BaseModel):
    customer_id: UUID
    balance: Decimal

    @field_serializer("balance")
    def serialize_balance(self, value: Decimal) -> str:
        return money_string(value)

