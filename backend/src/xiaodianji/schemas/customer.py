from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CustomerCandidate(BaseModel):
    customer_id: UUID
    name: str
    score: Decimal
    matched_on: str


class CustomerMatch(BaseModel):
    customer_id: UUID | None
    candidates: list[CustomerCandidate]
    confidence: Decimal
    requires_confirmation: bool
    normalized_query: str


class CustomerSummary(BaseModel):
    id: UUID
    name: str
    aliases: list[str]

