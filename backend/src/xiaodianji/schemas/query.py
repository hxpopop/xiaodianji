from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class QueryResponse(BaseModel):
    answer: str
    amount: str | None = None
    calculation_basis: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    ambiguity: dict[str, Any] | None = None
