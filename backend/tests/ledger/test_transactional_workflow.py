import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.models import (
    Base,
    ConfirmationEvent,
    ConfirmationStatus,
    Customer,
    CustomerAlias,
    PendingConfirmation,
    Shop,
    Transaction,
    TransactionItem,
)
from xiaodianji.schemas.record import PaymentDraft, TransactionDraft


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    (
        "postgresql+psycopg://xiaodianji:xiaodianji_test"
        "@127.0.0.1:55432/xiaodianji_test"
    ),
)


@pytest.fixture
async def database():
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    except OSError as error:
        await engine.dispose()
        pytest.skip(f"PostgreSQL integration database is unavailable: {error}")

    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    customer_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="测试五金店"))
        await session.flush()
        customer = Customer(
            id=customer_id,
            shop_id=shop_id,
            name="王建国",
            normalized_name="王建国",
        )
        customer.aliases.append(
            CustomerAlias(
                shop_id=shop_id,
                alias="王老板",
                normalized_alias="王",
            )
        )
        session.add(customer)

    yield factory, shop_id, customer_id
    await engine.dispose()


def two_item_debt() -> TransactionDraft:
    return TransactionDraft.model_validate(
        {
            "target_type": "transaction",
            "customer_name": "王老板",
            "occurred_at": "2026-07-27T10:00:00+08:00",
            "payment_status": "unpaid",
            "items": [
                {
                    "product": "角磨机",
                    "spec": "800W",
                    "quantity": "1",
                    "unit": "台",
                    "unit_price": "280.00",
                },
                {
                    "product": "切割片",
                    "quantity": "10",
                    "unit": "片",
                    "unit_price": "3.50",
                },
            ],
        }
    )


async def test_confirm_writes_parent_items_audit_and_balance_atomically(database) -> None:
    factory, shop_id, customer_id = database
    workflow = SQLAlchemyLedgerWorkflow(factory)
    pending = await workflow.create(shop_id, two_item_debt(), "manual-ledger-001")

    confirmed = await workflow.confirm(pending.id, "confirm-ledger-001")

    assert confirmed.status is ConfirmationStatus.CONFIRMED
    assert confirmed.formal_record_type == "transaction"
    async with factory() as session:
        transaction = await session.scalar(
            select(Transaction).where(Transaction.id == confirmed.formal_record_id)
        )
        items = (
            await session.scalars(
                select(TransactionItem)
                .where(TransactionItem.transaction_id == transaction.id)
                .order_by(TransactionItem.product)
            )
        ).all()
        event_types = (
            await session.scalars(
                select(ConfirmationEvent.event_type)
                .where(ConfirmationEvent.confirmation_id == pending.id)
                .order_by(ConfirmationEvent.created_at)
            )
        ).all()

    assert transaction.customer_id == customer_id
    assert transaction.total_amount == Decimal("315.00")
    assert [(item.product, item.subtotal) for item in items] == [
        ("切割片", Decimal("35.00")),
        ("角磨机", Decimal("280.00")),
    ]
    assert [event_type.value for event_type in event_types] == [
        "created",
        "confirmed",
    ]
    assert await workflow.customer_balance(shop_id, customer_id) == Decimal("315.00")


async def test_balance_is_unpaid_transactions_minus_payments(database) -> None:
    _, shop_id, customer_id = database
    workflow = SQLAlchemyLedgerWorkflow(database[0])
    debt = await workflow.create(shop_id, two_item_debt(), "manual-ledger-003")
    await workflow.confirm(debt.id, "confirm-ledger-003")
    payment = PaymentDraft.model_validate(
        {
            "target_type": "payment",
            "customer_name": "王老板",
            "paid_at": "2026-07-27T12:00:00+08:00",
            "amount": "95.00",
        }
    )
    pending_payment = await workflow.create(
        shop_id,
        payment,
        "manual-ledger-004",
    )
    await workflow.confirm(pending_payment.id, "confirm-ledger-004")

    assert await workflow.customer_balance(shop_id, customer_id) == Decimal("220.00")


async def test_item_insert_failure_rolls_back_formal_record_and_confirmation(database) -> None:
    factory, shop_id, _ = database
    workflow = SQLAlchemyLedgerWorkflow(factory)
    pending = await workflow.create(shop_id, two_item_debt(), "manual-ledger-002")
    calls = 0

    def fail_second_item(_mapper, _connection, _target) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated second item failure")

    event.listen(TransactionItem, "before_insert", fail_second_item)
    try:
        with pytest.raises(RuntimeError, match="simulated second item failure"):
            await workflow.confirm(pending.id, "confirm-ledger-002")
    finally:
        event.remove(TransactionItem, "before_insert", fail_second_item)

    async with factory() as session:
        transaction_count = await session.scalar(
            select(func.count()).select_from(Transaction)
        )
        item_count = await session.scalar(
            select(func.count()).select_from(TransactionItem)
        )
        stored_pending = await session.get(PendingConfirmation, pending.id)
        event_types = (
            await session.scalars(
                select(ConfirmationEvent.event_type)
                .where(ConfirmationEvent.confirmation_id == pending.id)
                .order_by(ConfirmationEvent.created_at)
            )
        ).all()

    assert transaction_count == 0
    assert item_count == 0
    assert stored_pending.status is ConfirmationStatus.PENDING
    assert stored_pending.formal_record_id is None
    assert [event_type.value for event_type in event_types] == ["created"]

