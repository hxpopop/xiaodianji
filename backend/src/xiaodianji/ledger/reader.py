from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.ledger.balance import BalanceService
from xiaodianji.ledger.service import LedgerService
from xiaodianji.models import Quote, Transaction


class LedgerReadService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        ledger_service: LedgerService | None = None,
        balance_service: BalanceService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.ledger_service = ledger_service or LedgerService()
        self.balance_service = balance_service or BalanceService(session_factory)

    async def get_transaction(
        self,
        shop_id: UUID,
        transaction_id: UUID,
    ) -> Transaction:
        async with self.session_factory() as session:
            return await self.ledger_service.get_transaction(
                session,
                shop_id,
                transaction_id,
            )

    async def get_quote(self, shop_id: UUID, quote_id: UUID) -> Quote:
        async with self.session_factory() as session:
            return await self.ledger_service.get_quote(session, shop_id, quote_id)

    async def customer_balance(
        self,
        shop_id: UUID,
        customer_id: UUID,
    ) -> Decimal:
        return await self.balance_service.customer_balance(shop_id, customer_id)


def ledger_reader_from(service: Any) -> Any:
    reader_methods = ("get_transaction", "get_quote", "customer_balance")
    if all(callable(getattr(service, name, None)) for name in reader_methods):
        return service
    return LedgerReadService(
        service.session_factory,
        ledger_service=service.ledger_service,
        balance_service=service.balance_service,
    )

