import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Customer, Shop
from xiaodianji.schemas.record import QuoteDraft, TransactionDraft


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    (
        "postgresql+psycopg://xiaodianji:xiaodianji_test"
        "@127.0.0.1:55432/xiaodianji_test"
    ),
)


@pytest.fixture
async def api_database():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    customer_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="接口测试店"))
        await session.flush()
        session.add(
            Customer(
                id=customer_id,
                shop_id=shop_id,
                name="李老板",
                normalized_name="李",
            )
        )
    yield factory, shop_id, customer_id
    await engine.dispose()


async def test_transaction_detail_and_customer_balance_return_money_strings(
    api_database,
) -> None:
    factory, shop_id, customer_id = api_database
    workflow = SQLAlchemyLedgerWorkflow(factory)
    draft = TransactionDraft.model_validate(
        {
            "target_type": "transaction",
            "customer_name": "李老板",
            "occurred_at": "2026-07-27T10:00:00+08:00",
            "payment_status": "unpaid",
            "items": [
                {
                    "product": "电钻",
                    "quantity": "2",
                    "unit": "台",
                    "unit_price": "199.50",
                }
            ],
        }
    )
    pending = await workflow.create(shop_id, draft, "manual-api-ledger-001")
    confirmed = await workflow.confirm(pending.id, "confirm-api-ledger-001")
    app = create_app(ledger_service=workflow)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        detail = await client.get(
            f"/api/v1/ledger/transactions/{confirmed.formal_record_id}",
            headers={"X-Shop-Id": str(shop_id)},
        )
        balance = await client.get(
            f"/api/v1/customers/{customer_id}/balance",
            headers={"X-Shop-Id": str(shop_id)},
        )

    assert detail.status_code == 200
    assert detail.json()["total_amount"] == "399.00"
    assert detail.json()["items"][0]["unit_price"] == "199.50"
    assert detail.json()["items"][0]["subtotal"] == "399.00"
    assert balance.status_code == 200
    assert balance.json() == {
        "customer_id": str(customer_id),
        "balance": "399.00",
    }


async def test_quote_detail_is_tenant_scoped(api_database) -> None:
    factory, shop_id, _ = api_database
    workflow = SQLAlchemyLedgerWorkflow(factory)
    draft = QuoteDraft.model_validate(
        {
            "target_type": "quote",
            "customer_name": "李老板",
            "quoted_at": "2026-07-27T10:00:00+08:00",
            "items": [
                {
                    "product": "电焊机",
                    "quantity": "1",
                    "unit": "台",
                    "unit_price": "880.00",
                }
            ],
        }
    )
    pending = await workflow.create(shop_id, draft, "manual-api-ledger-002")
    confirmed = await workflow.confirm(pending.id, "confirm-api-ledger-002")
    app = create_app(ledger_service=workflow)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        found = await client.get(
            f"/api/v1/ledger/quotes/{confirmed.formal_record_id}",
            headers={"X-Shop-Id": str(shop_id)},
        )
        hidden = await client.get(
            f"/api/v1/ledger/quotes/{confirmed.formal_record_id}",
            headers={"X-Shop-Id": str(uuid4())},
        )

    assert found.status_code == 200
    assert found.json()["total_amount"] == "880.00"
    assert hidden.status_code == 404

