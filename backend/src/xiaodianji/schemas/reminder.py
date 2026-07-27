from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderItem(BaseModel):
    customer_id: UUID
    customer_name: str
    due_at: datetime
    balance: Decimal
    overdue_transaction_count: int = Field(ge=1)
    overdue_days: int = Field(ge=1)


class ReminderSummary(BaseModel):
    overdue_count: int = Field(ge=0)
    items: list[ReminderItem]


class RefreshRemindersRequest(BaseModel):
    as_of: date | None = None
