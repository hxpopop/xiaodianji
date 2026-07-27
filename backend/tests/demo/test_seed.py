from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.demo.seed import DEMO_IDS, seed_demo
from xiaodianji.models import (
    Base,
    Customer,
    CustomerAlias,
    Evidence,
    Payment,
    Quote,
    Reminder,
    Shop,
    Transaction,
)


TEST_DATABASE_URL = (
    "postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test"
)


async def test_demo_seed_is_idempotent_and_creates_complete_story() -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    first = await seed_demo(factory)
    second = await seed_demo(factory)

    assert first == second
    assert first["shop"] == str(DEMO_IDS["shop"])
    async with factory() as session:
        for model in (
            Shop,
            Customer,
            CustomerAlias,
            Evidence,
            Quote,
            Transaction,
            Payment,
            Reminder,
        ):
            assert await session.scalar(select(func.count()).select_from(model)) == 1
        customer = await session.get(Customer, DEMO_IDS["customer"])
        transaction = await session.get(Transaction, DEMO_IDS["transaction"])
        assert customer is not None and customer.name == "王老板"
        assert transaction is not None and str(transaction.total_amount) == "500.00"

    await engine.dispose()
