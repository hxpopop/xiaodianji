from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.ledger.service import LedgerNotFound
from xiaodianji.models import Customer, Payment, PaymentStatus, Transaction


CENT = Decimal("0.01")


class BalanceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.session_factory = session_factory

    async def customer_balance(
        self,
        shop_id: UUID,
        customer_id: UUID,
    ) -> Decimal:
        unpaid_total = (
            select(func.coalesce(func.sum(Transaction.total_amount), 0))
            .where(
                Transaction.shop_id == shop_id,
                Transaction.customer_id == customer_id,
                Transaction.payment_status == PaymentStatus.UNPAID,
            )
            .scalar_subquery()
        )
        payment_total = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.shop_id == shop_id,
                Payment.customer_id == customer_id,
            )
            .scalar_subquery()
        )
        statement = (
            select(unpaid_total - payment_total)
            .select_from(Customer)
            .where(
                Customer.id == customer_id,
                Customer.shop_id == shop_id,
            )
        )
        async with self.session_factory() as session:
            row = (await session.execute(statement)).one_or_none()
        if row is None:
            raise LedgerNotFound(str(customer_id))
        return Decimal(row[0]).quantize(CENT)

