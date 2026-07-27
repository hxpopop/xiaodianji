from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from xiaodianji.customers.service import CustomerRecord
from xiaodianji.models import Customer


class SQLAlchemyCustomerRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.session_factory = session_factory

    async def list_for_shop(self, shop_id: UUID) -> list[CustomerRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Customer)
                .where(Customer.shop_id == shop_id)
                .options(selectinload(Customer.aliases))
                .order_by(Customer.name, Customer.id)
            )
            customers = result.scalars().unique().all()
        return [
            CustomerRecord(
                customer_id=customer.id,
                name=customer.name,
                aliases=tuple(alias.alias for alias in customer.aliases),
            )
            for customer in customers
        ]

