import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import xiaodianji.reminders.service as reminder_service_module
from xiaodianji.main import create_app
from xiaodianji.models import Base, Customer, Payment, PaymentStatus, Reminder, ReminderStatus, Shop, Transaction
from xiaodianji.reminders.service import ReminderService


TEST_DATABASE_URL = "postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test"


@pytest.fixture
async def reminder_database():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {"shop": uuid4(), "customer": uuid4(), "other_shop": uuid4(), "other_customer": uuid4()}
    async with factory.begin() as session:
        session.add_all([Shop(id=ids["shop"], name="本店", timezone="Asia/Shanghai"), Shop(id=ids["other_shop"], name="外店", timezone="Asia/Shanghai")])
        await session.flush()
        session.add_all([
            Customer(id=ids["customer"], shop_id=ids["shop"], name="王老板", normalized_name="王"),
            Customer(id=ids["other_customer"], shop_id=ids["other_shop"], name="外店客户", normalized_name="外店客户"),
        ])
    yield factory, ids
    await engine.dispose()


async def _add_transaction(factory, *, shop_id, customer_id, occurred_at: datetime, amount: str = "100.00") -> None:
    async with factory.begin() as session:
        session.add(Transaction(shop_id=shop_id, customer_id=customer_id, occurred_at=occurred_at, payment_status=PaymentStatus.UNPAID, total_amount=Decimal(amount)))


async def test_old_unpaid_transaction_creates_one_customer_reminder(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 6, 1, 10, tzinfo=timezone.utc))
    summary = await ReminderService(factory).refresh(ids["shop"], date(2026, 7, 2))
    assert summary.overdue_count == 1
    item = summary.items[0]
    assert item.customer_id == ids["customer"]
    assert item.customer_name == "王老板"
    assert item.balance == Decimal("100.00")
    assert item.overdue_transaction_count == 1
    assert item.overdue_days == 1


async def test_due_date_boundary_does_not_create_reminder_early(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 6, 1, 10, tzinfo=timezone.utc))
    summary = await ReminderService(factory).refresh(ids["shop"], date(2026, 7, 1))
    assert summary.overdue_count == 0


async def test_repeat_refresh_reuses_reminder_and_aggregates_old_transactions(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc), amount="100.00")
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 15, 10, tzinfo=timezone.utc), amount="50.00")
    service = ReminderService(factory)
    first = await service.refresh(ids["shop"], date(2026, 7, 2))
    second = await service.refresh(ids["shop"], date(2026, 7, 2))
    async with factory() as session:
        reminders = list((await session.scalars(select(Reminder).where(Reminder.shop_id == ids["shop"]))).all())
    assert first.overdue_count == second.overdue_count == 1
    assert second.items[0].overdue_transaction_count == 2
    assert second.items[0].balance == Decimal("150.00")
    assert len(reminders) == 1


async def test_payment_that_zeros_customer_balance_resolves_open_reminder(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    service = ReminderService(factory)
    await service.refresh(ids["shop"], date(2026, 7, 2))
    async with factory.begin() as session:
        session.add(Payment(shop_id=ids["shop"], customer_id=ids["customer"], amount=Decimal("100.00"), paid_at=datetime(2026, 7, 2, 10, tzinfo=timezone.utc)))
    summary = await service.refresh(ids["shop"], date(2026, 7, 3))
    async with factory() as session:
        reminder = await session.scalar(select(Reminder).where(Reminder.shop_id == ids["shop"]))
    assert summary.overdue_count == 0
    assert reminder is not None
    assert reminder.status == ReminderStatus.RESOLVED


async def test_refresh_and_list_are_tenant_scoped(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    await _add_transaction(factory, shop_id=ids["other_shop"], customer_id=ids["other_customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    service = ReminderService(factory)
    await service.refresh(ids["shop"], date(2026, 7, 2))
    hidden = await service.list_open(ids["other_shop"])
    visible = await service.list_open(ids["shop"])
    assert hidden.overdue_count == 0
    assert visible.overdue_count == 1
    assert visible.items[0].customer_name == "王老板"


async def test_get_and_refresh_api_return_only_reminder_summary_fields(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    app = create_app(reminder_service=ReminderService(factory))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        refreshed = await client.post("/api/v1/reminders/refresh", headers={"X-Shop-Id": str(ids["shop"])}, json={"as_of": "2026-07-02"})
        listed = await client.get("/api/v1/reminders", headers={"X-Shop-Id": str(ids["shop"])})
    assert refreshed.status_code == listed.status_code == 200
    body = listed.json()
    assert body["overdue_count"] == 1
    assert set(body["items"][0]) == {"customer_id", "customer_name", "due_at", "balance", "overdue_transaction_count", "overdue_days"}
    assert body["items"][0]["balance"] == "100.00"


async def test_list_open_uses_shop_local_due_date_after_postgres_round_trip(reminder_database, monkeypatch) -> None:
    factory, ids = reminder_database
    fixed_now = datetime(2026, 7, 2, 12, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now.astimezone(tz) if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(reminder_service_module, "datetime", FixedDatetime)
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    service = ReminderService(factory)
    await service.refresh(ids["shop"], date(2026, 7, 2))

    summary = await service.list_open(ids["shop"])

    assert summary.items[0].overdue_days == 32


async def test_concurrent_refreshes_create_only_one_reminder(reminder_database) -> None:
    factory, ids = reminder_database
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc))
    service = ReminderService(factory)

    results = await asyncio.gather(
        service.refresh(ids["shop"], date(2026, 7, 2)),
        service.refresh(ids["shop"], date(2026, 7, 2)),
    )
    async with factory() as session:
        reminders = list((await session.scalars(select(Reminder).where(Reminder.shop_id == ids["shop"]))).all())

    assert [result.overdue_count for result in results] == [1, 1]
    assert len(reminders) == 1


async def test_omitted_refresh_date_uses_requested_shop_timezone(reminder_database) -> None:
    factory, ids = reminder_database
    fixed_now = datetime(2026, 7, 2, 2, tzinfo=timezone.utc)
    async with factory.begin() as session:
        shop = await session.get(Shop, ids["shop"])
        assert shop is not None
        shop.timezone = "America/Los_Angeles"
    await _add_transaction(factory, shop_id=ids["shop"], customer_id=ids["customer"], occurred_at=datetime(2026, 6, 1, 12, tzinfo=timezone.utc))
    app = create_app(reminder_service=ReminderService(factory, now=lambda: fixed_now))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/reminders/refresh", headers={"X-Shop-Id": str(ids["shop"])}, json={})

    assert response.status_code == 200
    assert response.json()["overdue_count"] == 0
