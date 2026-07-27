from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, PendingConfirmation, Shop, Transaction
from xiaodianji.providers.fake import FakeASRProvider, FakeExtractionProvider
from xiaodianji.records.extraction import RecordWorkflow


async def test_text_record_creates_two_item_pending_confirmation() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="智能记账测试店"))

    workflow = SQLAlchemyLedgerWorkflow(factory)
    app = create_app(
        record_workflow=RecordWorkflow(
            confirmation_workflow=workflow,
            extraction_provider=FakeExtractionProvider(),
            asr_provider=FakeASRProvider(),
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/records/text",
            headers={
                "X-Shop-Id": str(shop_id),
                "Idempotency-Key": "text-001",
            },
            json={"text": "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert len(body["effective_json"]["items"]) == 2
    assert body["effective_json"]["total_amount"] == "420.00"
    assert body["field_confidences"]["items.1.quantity"] == "0.62"

    async with factory() as session:
        pending_count = await session.scalar(select(func.count()).select_from(PendingConfirmation))
        transaction_count = await session.scalar(select(func.count()).select_from(Transaction))
    assert pending_count == 1
    assert transaction_count == 0
    await engine.dispose()
