from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from rapidfuzz.fuzz import ratio

from xiaodianji.customers.normalization import normalize_customer_name
from xiaodianji.schemas.customer import (
    CustomerCandidate,
    CustomerMatch,
    CustomerSummary,
)


@dataclass(frozen=True, slots=True)
class CustomerRecord:
    customer_id: UUID
    name: str
    aliases: tuple[str, ...]


class CustomerRepository(Protocol):
    async def list_for_shop(self, shop_id: UUID) -> list[CustomerRecord]: ...


class CustomerService:
    def __init__(
        self,
        repository: CustomerRepository,
        *,
        fuzzy_threshold: int = 70,
        candidate_limit: int = 5,
    ) -> None:
        self.repository = repository
        self.fuzzy_threshold = fuzzy_threshold
        self.candidate_limit = candidate_limit

    async def list_summaries(self, shop_id: UUID) -> list[CustomerSummary]:
        records = await self.repository.list_for_shop(shop_id)
        return [
            CustomerSummary(
                id=record.customer_id,
                name=record.name,
                aliases=list(record.aliases),
            )
            for record in records
        ]

    async def match(self, shop_id: UUID, spoken_name: str) -> CustomerMatch:
        normalized_query = normalize_customer_name(spoken_name)
        records = await self.repository.list_for_shop(shop_id)

        exact_candidates = self._exact_candidates(records, normalized_query)
        if len(exact_candidates) == 1:
            selected = exact_candidates[0]
            return CustomerMatch(
                customer_id=selected.customer_id,
                candidates=exact_candidates,
                confidence=Decimal("1"),
                requires_confirmation=False,
                normalized_query=normalized_query,
            )
        if len(exact_candidates) > 1:
            return CustomerMatch(
                customer_id=None,
                candidates=exact_candidates,
                confidence=Decimal("0"),
                requires_confirmation=True,
                normalized_query=normalized_query,
            )

        fuzzy_candidates = self._fuzzy_candidates(records, normalized_query)
        return CustomerMatch(
            customer_id=None,
            candidates=fuzzy_candidates,
            confidence=(
                fuzzy_candidates[0].score if fuzzy_candidates else Decimal("0")
            ),
            requires_confirmation=True,
            normalized_query=normalized_query,
        )

    @staticmethod
    def _exact_candidates(
        records: list[CustomerRecord],
        normalized_query: str,
    ) -> list[CustomerCandidate]:
        candidates: list[CustomerCandidate] = []
        for record in records:
            normalized_name = normalize_customer_name(record.name)
            normalized_aliases = {
                normalize_customer_name(alias) for alias in record.aliases
            }
            if normalized_query == normalized_name:
                matched_on = "name"
            elif normalized_query in normalized_aliases:
                matched_on = "alias"
            else:
                continue
            candidates.append(
                CustomerCandidate(
                    customer_id=record.customer_id,
                    name=record.name,
                    score=Decimal("1"),
                    matched_on=matched_on,
                )
            )
        return candidates

    def _fuzzy_candidates(
        self,
        records: list[CustomerRecord],
        normalized_query: str,
    ) -> list[CustomerCandidate]:
        if not normalized_query:
            return []

        candidates: list[CustomerCandidate] = []
        for record in records:
            comparison_values = [
                normalize_customer_name(record.name),
                *(normalize_customer_name(alias) for alias in record.aliases),
            ]
            best_score = max(
                (ratio(normalized_query, value) for value in comparison_values if value),
                default=0,
            )
            if best_score < self.fuzzy_threshold:
                continue
            candidates.append(
                CustomerCandidate(
                    customer_id=record.customer_id,
                    name=record.name,
                    score=Decimal(str(best_score / 100)).quantize(
                        Decimal("0.0001")
                    ),
                    matched_on="fuzzy",
                )
            )
        return sorted(
            candidates,
            key=lambda candidate: (-candidate.score, candidate.name),
        )[: self.candidate_limit]

