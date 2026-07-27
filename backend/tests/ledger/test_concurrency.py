import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.confirmations.service import ConfirmationConflict
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.models import (
    Base,
    ConfirmationEvent,
    ConfirmationEventType,
    Shop,
    Transaction,
)
from xiaodianji.schemas.record import TransactionDraft


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    (
        "postgresql+psycopg://xiaodianji:xiaodianji_test"
        "@127.0.0.1:55432/xiaodianji_test"
    ),
)


@pytest.fixture
async def concurrent_database():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="并发测试店"))
    yield factory, shop_id
    await engine.dispose()


def debt_draft() -> TransactionDraft:
    return TransactionDraft.model_validate(
        {
            "target_type": "transaction",
            "customer_name": "赵老板",
            "occurred_at": "2026-07-27T10:00:00+08:00",
            "payment_status": "unpaid",
            "items": [
                {
                    "product": "扳手",
                    "quantity": "1",
                    "unit": "把",
                    "unit_price": "35.00",
                }
            ],
        }
    )


async def test_concurrent_creation_with_same_key_returns_one_confirmation(
    concurrent_database,
) -> None:
    factory, shop_id = concurrent_database
    first_workflow = SQLAlchemyLedgerWorkflow(factory)
    second_workflow = SQLAlchemyLedgerWorkflow(factory)

    first, second = await asyncio.gather(
        first_workflow.create(shop_id, debt_draft(), "same-create-key"),
        second_workflow.create(shop_id, debt_draft(), "same-create-key"),
    )

    async with factory() as session:
        created_events = await session.scalar(
            select(func.count())
            .select_from(ConfirmationEvent)
            .where(ConfirmationEvent.event_type == ConfirmationEventType.CREATED)
        )
    assert first.id == second.id
    assert created_events == 1


async def test_concurrent_confirmation_with_same_key_writes_once(
    concurrent_database,
) -> None:
    factory, shop_id = concurrent_database
    first_workflow = SQLAlchemyLedgerWorkflow(factory)
    second_workflow = SQLAlchemyLedgerWorkflow(factory)
    pending = await first_workflow.create(
        shop_id,
        debt_draft(),
        "confirm-concurrent-source",
    )

    first, second = await asyncio.gather(
        first_workflow.confirm(pending.id, "same-confirm-key"),
        second_workflow.confirm(pending.id, "same-confirm-key"),
    )

    async with factory() as session:
        transaction_count = await session.scalar(
            select(func.count()).select_from(Transaction)
        )
        confirmed_events = await session.scalar(
            select(func.count())
            .select_from(ConfirmationEvent)
            .where(
                ConfirmationEvent.event_type
                == ConfirmationEventType.CONFIRMED
            )
        )
    assert first.formal_record_id == second.formal_record_id
    assert transaction_count == 1
    assert confirmed_events == 1


async def test_concurrent_confirmation_with_different_key_conflicts(
    concurrent_database,
) -> None:
    factory, shop_id = concurrent_database
    first_workflow = SQLAlchemyLedgerWorkflow(factory)
    second_workflow = SQLAlchemyLedgerWorkflow(factory)
    pending = await first_workflow.create(
        shop_id,
        debt_draft(),
        "confirm-conflict-source",
    )

    results = await asyncio.gather(
        first_workflow.confirm(pending.id, "confirm-key-a"),
        second_workflow.confirm(pending.id, "confirm-key-b"),
        return_exceptions=True,
    )

    assert sum(isinstance(result, ConfirmationConflict) for result in results) == 1
    async with factory() as session:
        assert await session.scalar(
            select(func.count()).select_from(Transaction)
        ) == 1

