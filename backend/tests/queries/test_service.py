from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from xiaodianji.customers.repository import SQLAlchemyCustomerRepository
from xiaodianji.customers.service import CustomerService
from xiaodianji.main import create_app
from xiaodianji.models import Anomaly, Base, Customer, CustomerAlias, Evidence, EvidenceStatus, EvidenceType, Payment, PaymentStatus, PendingConfirmation, Quote, QuoteItem, Reminder, ReminderStatus, Shop, Transaction, TransactionItem
from xiaodianji.models.confirmation import ConfirmationStatus, ConfirmationTargetType
from xiaodianji.queries.service import QueryService

TEST_DATABASE_URL = "postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test"


@pytest.fixture
async def query_seed():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id, other_shop_id = uuid4(), uuid4()
    customer_id, wang_one_id, wang_two_id = uuid4(), uuid4(), uuid4()
    evidence_id, other_evidence_id = uuid4(), uuid4()
    async with factory.begin() as session:
        session.add_all([Shop(id=shop_id, name="查询店", timezone="Asia/Shanghai"), Shop(id=other_shop_id, name="隔离店", timezone="Asia/Shanghai")])
        await session.flush()
        session.add_all([
            Customer(id=customer_id, shop_id=shop_id, name="李建材", normalized_name="李建材"),
            Customer(id=wang_one_id, shop_id=shop_id, name="王老板", normalized_name="王"),
            Customer(id=wang_two_id, shop_id=shop_id, name="王师傅", normalized_name="王"),
            CustomerAlias(shop_id=shop_id, customer_id=customer_id, alias="李老板", normalized_alias="李"),
            Evidence(id=evidence_id, shop_id=shop_id, type=EvidenceType.TEXT, status=EvidenceStatus.READY, object_key="query/own.txt", mime_type="text/plain", size_bytes=10),
            Evidence(id=other_evidence_id, shop_id=other_shop_id, type=EvidenceType.TEXT, status=EvidenceStatus.READY, object_key="query/other.txt", mime_type="text/plain", size_bytes=10),
        ])
        await session.flush()
        transaction = Transaction(shop_id=shop_id, customer_id=customer_id, occurred_at=datetime(2026, 7, 27, 1, tzinfo=timezone.utc), payment_status=PaymentStatus.UNPAID, total_amount=Decimal("300.00"), source_evidence_id=evidence_id)
        transaction.items.append(TransactionItem(product="插座", quantity=Decimal("3"), unit="个", unit_price=Decimal("100.00"), subtotal=Decimal("300.00")))
        quote = Quote(shop_id=shop_id, customer_id=customer_id, quoted_at=datetime(2026, 7, 27, 1, tzinfo=timezone.utc), total_amount=Decimal("80.00"), source_evidence_id=evidence_id)
        quote.items.append(QuoteItem(product="插座", quantity=Decimal("2"), unit="个", unit_price=Decimal("40.00"), subtotal=Decimal("80.00")))
        session.add_all([
            transaction, quote,
            Payment(shop_id=shop_id, customer_id=customer_id, amount=Decimal("80.00"), paid_at=datetime(2026, 7, 27, 2, tzinfo=timezone.utc), source_evidence_id=evidence_id),
            Reminder(shop_id=shop_id, customer_id=customer_id, type="overdue", due_at=datetime(2026, 6, 1, tzinfo=timezone.utc), status=ReminderStatus.OPEN, payload={"balance": "220.00"}),
            Reminder(shop_id=other_shop_id, customer_id=None, type="overdue", due_at=datetime(2026, 6, 1, tzinfo=timezone.utc), status=ReminderStatus.OPEN, payload={"balance": "999.00"}),
            PendingConfirmation(shop_id=shop_id, target_type=ConfirmationTargetType.TRANSACTION, extracted_json={"customer_name": "李建材"}, field_confidences={}, status=ConfirmationStatus.PENDING, idempotency_key="query-pending-own", source_evidence_id=evidence_id),
            PendingConfirmation(shop_id=other_shop_id, target_type=ConfirmationTargetType.TRANSACTION, extracted_json={"customer_name": "外店客户"}, field_confidences={}, status=ConfirmationStatus.PENDING, idempotency_key="query-pending-other", source_evidence_id=other_evidence_id),
            Anomaly(shop_id=shop_id, type="amount_mismatch", severity="warning", status=ReminderStatus.OPEN, payload={"message": "金额不一致"}),
            Anomaly(shop_id=other_shop_id, type="amount_mismatch", severity="warning", status=ReminderStatus.OPEN, payload={"message": "不应泄漏"}),
        ])
    yield factory, shop_id, other_shop_id, evidence_id
    await engine.dispose()


def _service(factory) -> QueryService:
    return QueryService(factory, CustomerService(SQLAlchemyCustomerRepository(factory)), now=lambda: datetime(2026, 7, 27, 4, tzinfo=timezone.utc))


async def test_balance_uses_debt_minus_payments_and_returns_only_own_evidence(query_seed) -> None:
    factory, shop_id, _, evidence_id = query_seed
    result = await _service(factory).query(shop_id, "李老板还欠多少钱")
    assert result.amount == "220.00"
    assert result.calculation_basis == "赊账交易总额 - 收款总额"
    assert {detail["type"] for detail in result.details} == {"transaction", "payment"}
    assert result.evidence_ids == [evidence_id]
    assert result.ambiguity is None


async def test_ambiguous_customer_does_not_return_an_amount(query_seed) -> None:
    factory, shop_id, _, _ = query_seed
    result = await _service(factory).query(shop_id, "王还欠多少钱")
    assert result.amount is None
    assert result.ambiguity is not None
    assert {candidate["name"] for candidate in result.ambiguity["candidates"]} == {"王老板", "王师傅"}


async def test_quote_product_filter_daily_boundary_and_non_balance_lists_are_shop_scoped(query_seed) -> None:
    factory, shop_id, other_shop_id, _ = query_seed
    service = _service(factory)
    quote = await service.query(shop_id, "上次给李老板报的插座多少钱")
    daily = await service.query(shop_id, "今天一共卖了多少")
    overdue = await service.query(shop_id, "哪些账逾期了")
    pending = await service.query(shop_id, "有哪些待确认")
    anomaly = await service.query(shop_id, "最近有哪些异常")
    other_shop = await service.query(other_shop_id, "哪些账逾期了")
    assert quote.amount == "80.00"
    assert quote.details[0]["product"] == "插座"
    assert daily.amount == "380.00"
    assert {detail["type"] for detail in daily.details} == {"transaction", "payment"}
    assert len(overdue.details) == len(pending.details) == len(anomaly.details) == 1
    assert overdue.details[0]["customer_name"] == "李建材"
    assert pending.details[0]["customer_name"] == "李建材"
    assert anomaly.details[0]["message"] == "金额不一致"
    assert other_shop.details[0]["customer_name"] is None


async def test_query_api_returns_domain_response_for_supported_and_unknown_questions(query_seed) -> None:
    factory, shop_id, _, evidence_id = query_seed
    app = create_app(query_service=_service(factory))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        supported = await client.post("/api/v1/queries", headers={"X-Shop-Id": str(shop_id)}, json={"question": "李老板还欠多少钱"})
        unknown = await client.post("/api/v1/queries", headers={"X-Shop-Id": str(shop_id)}, json={"question": "帮我算算哪种货最赚钱"})
    assert supported.status_code == 200
    assert supported.json()["amount"] == "220.00"
    assert supported.json()["evidence_ids"] == [str(evidence_id)]
    assert unknown.status_code == 200
    assert unknown.json()["amount"] is None
    assert "不支持" in unknown.json()["answer"]
