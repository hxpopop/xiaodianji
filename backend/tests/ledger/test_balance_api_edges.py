import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Customer, Shop


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    (
        "postgresql+psycopg://xiaodianji:xiaodianji_test"
        "@127.0.0.1:55432/xiaodianji_test"
    ),
)


@pytest.fixture
async def balance_database():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    other_shop_id = uuid4()
    customer_id = uuid4()
    async with factory.begin() as session:
        session.add_all(
            [
                Shop(id=shop_id, name="余额测试店"),
                Shop(id=other_shop_id, name="另一家店"),
            ]
        )
        await session.flush()
        session.add(
            Customer(
                id=customer_id,
                shop_id=shop_id,
                name="无账客户",
                normalized_name="无账客户",
            )
        )
    yield factory, shop_id, other_shop_id, customer_id
    await engine.dispose()


async def test_zero_balance_is_fixed_two_decimal_string(balance_database) -> None:
    factory, shop_id, _, customer_id = balance_database
    app = create_app(ledger_service=SQLAlchemyLedgerWorkflow(factory))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/customers/{customer_id}/balance",
            headers={"X-Shop-Id": str(shop_id)},
        )

    assert response.status_code == 200
    assert response.json()["balance"] == "0.00"


@pytest.mark.parametrize("use_other_shop", [False, True])
async def test_missing_or_cross_tenant_customer_balance_is_not_found(
    balance_database,
    use_other_shop,
) -> None:
    factory, shop_id, other_shop_id, customer_id = balance_database
    requested_shop_id = other_shop_id if use_other_shop else shop_id
    requested_customer_id = customer_id if use_other_shop else uuid4()
    app = create_app(ledger_service=SQLAlchemyLedgerWorkflow(factory))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/customers/{requested_customer_id}/balance",
            headers={"X-Shop-Id": str(requested_shop_id)},
        )

    assert response.status_code == 404

