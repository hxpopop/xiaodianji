import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.customers.normalization import normalize_customer_name
from xiaodianji.db import async_session_factory
from xiaodianji.models import (
    Customer,
    CustomerAlias,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Payment,
    PaymentStatus,
    Quote,
    QuoteItem,
    Reminder,
    ReminderStatus,
    Shop,
    Transaction,
    TransactionItem,
)


DEMO_IDS = {
    key: UUID(f"00000000-0000-0000-0000-{number:012d}")
    for key, number in {
        "shop": 101, "customer": 102, "alias": 103, "evidence": 104,
        "quote": 105, "quote_item": 106, "transaction": 107,
        "transaction_item_1": 108, "transaction_item_2": 109,
        "payment": 110, "reminder": 111,
    }.items()
}


def _records() -> list[object]:
    shop = DEMO_IDS["shop"]
    customer = DEMO_IDS["customer"]
    evidence = DEMO_IDS["evidence"]
    return [
        Shop(id=shop, name="小店记演示商户", timezone="Asia/Shanghai"),
        Customer(
            id=customer,
            shop_id=shop,
            name="王老板",
            normalized_name=normalize_customer_name("王老板"),
            phone="13800000000",
            notes="比赛演示客户",
        ),
        CustomerAlias(
            id=DEMO_IDS["alias"],
            shop_id=shop,
            customer_id=customer,
            alias="老王",
            normalized_alias=normalize_customer_name("老王"),
        ),
        Evidence(
            id=evidence,
            shop_id=shop,
            type=EvidenceType.AUDIO,
            status=EvidenceStatus.READY,
            object_key="demo/two-items.wav",
            original_filename="two-items.wav",
            mime_type="audio/wav",
            size_bytes=128,
            asr_text="王老板赊账角磨机两台，插座七个，共五百元",
        ),
        Quote(
            id=DEMO_IDS["quote"],
            shop_id=shop,
            customer_id=customer,
            quoted_at=datetime(2026, 5, 20, 9, tzinfo=timezone.utc),
            total_amount=Decimal("360.00"),
            source_evidence_id=evidence,
        ),
        QuoteItem(
            id=DEMO_IDS["quote_item"],
            quote_id=DEMO_IDS["quote"],
            product="角磨机",
            spec="800W",
            quantity=Decimal("2"),
            unit="台",
            unit_price=Decimal("180.00"),
            subtotal=Decimal("360.00"),
        ),
        Transaction(
            id=DEMO_IDS["transaction"],
            shop_id=shop,
            customer_id=customer,
            occurred_at=datetime(2026, 5, 25, 10, tzinfo=timezone.utc),
            payment_status=PaymentStatus.UNPAID,
            total_amount=Decimal("500.00"),
            source_evidence_id=evidence,
        ),
        TransactionItem(
            id=DEMO_IDS["transaction_item_1"],
            transaction_id=DEMO_IDS["transaction"],
            product="角磨机",
            spec="800W",
            quantity=Decimal("2"),
            unit="台",
            unit_price=Decimal("180.00"),
            subtotal=Decimal("360.00"),
        ),
        TransactionItem(
            id=DEMO_IDS["transaction_item_2"],
            transaction_id=DEMO_IDS["transaction"],
            product="插座",
            spec="五孔",
            quantity=Decimal("7"),
            unit="个",
            unit_price=Decimal("20.00"),
            subtotal=Decimal("140.00"),
        ),
        Payment(
            id=DEMO_IDS["payment"],
            shop_id=shop,
            customer_id=customer,
            amount=Decimal("80.00"),
            paid_at=datetime(2026, 6, 1, 10, tzinfo=timezone.utc),
            source_evidence_id=None,
        ),
        Reminder(
            id=DEMO_IDS["reminder"],
            shop_id=shop,
            customer_id=customer,
            type="overdue",
            due_at=datetime(2026, 6, 24, 10, tzinfo=timezone.utc),
            status=ReminderStatus.OPEN,
            payload={
                "source": "demo-seed",
                "balance": "420.00",
                "overdue_transaction_count": 1,
            },
        ),
    ]


async def seed_demo(
    factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> dict[str, str]:
    async with factory.begin() as session:
        for record in _records():
            if await session.get(type(record), record.id) is None:
                session.add(record)
                await session.flush()

        customer = await session.get(Customer, DEMO_IDS["customer"])
        if customer is not None:
            customer.normalized_name = normalize_customer_name(customer.name)

        reminder = await session.get(Reminder, DEMO_IDS["reminder"])
        if reminder is not None:
            reminder.status = ReminderStatus.OPEN
            reminder.payload = {
                "source": "demo-seed",
                "balance": "420.00",
                "overdue_transaction_count": 1,
            }
    return {key: str(value) for key, value in DEMO_IDS.items()}


def main() -> None:
    ids = asyncio.run(seed_demo())
    print(f"Demo seeded. XDJ_DEMO_SHOP_ID={ids['shop']}")


if __name__ == "__main__":
    main()
