from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from xiaodianji.models import PaymentStatus


CENT = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class DraftModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LineItemDraft(DraftModel):
    product: str = Field(min_length=1, max_length=200)
    spec: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit: str = Field(min_length=1, max_length=30)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    subtotal: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)

    @field_validator("product", "unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped

    @model_validator(mode="after")
    def calculate_subtotal(self) -> "LineItemDraft":
        self.subtotal = quantize_money(self.quantity * self.unit_price)
        return self


class ItemRecordDraft(DraftModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_id: UUID | None = None
    items: list[LineItemDraft] = Field(min_length=1)
    total_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)

    @field_validator("customer_name")
    @classmethod
    def strip_customer_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("customer_name must not be blank")
        return stripped

    @model_validator(mode="after")
    def calculate_total(self) -> "ItemRecordDraft":
        self.total_amount = quantize_money(
            sum((item.subtotal for item in self.items), start=Decimal("0"))
        )
        return self


class QuoteDraft(ItemRecordDraft):
    target_type: Literal["quote"]
    quoted_at: datetime


class TransactionDraft(ItemRecordDraft):
    target_type: Literal["transaction"]
    occurred_at: datetime
    payment_status: PaymentStatus


class PaymentDraft(DraftModel):
    target_type: Literal["payment"]
    customer_name: str = Field(min_length=1, max_length=120)
    customer_id: UUID | None = None
    paid_at: datetime
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)

    @field_validator("customer_name")
    @classmethod
    def strip_customer_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("customer_name must not be blank")
        return stripped

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


RecordDraft = Annotated[
    QuoteDraft | TransactionDraft | PaymentDraft,
    Field(discriminator="target_type"),
]
record_draft_adapter = TypeAdapter(RecordDraft)
