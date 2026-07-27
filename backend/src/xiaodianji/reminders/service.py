from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.ledger.balance import BalanceService
from xiaodianji.models import Customer, PaymentStatus, Reminder, ReminderStatus, Shop, Transaction
from xiaodianji.schemas.reminder import ReminderItem, ReminderSummary


CENT = Decimal("0.01")
OVERDUE_TYPE = "overdue"


class ReminderService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        overdue_days: int = 30,
    ) -> None:
        if overdue_days <= 0:
            raise ValueError("overdue_days must be positive")
        self.session_factory = session_factory
        self.overdue_days = overdue_days
        self.balance_service = BalanceService(session_factory)

    async def refresh(self, shop_id: UUID, as_of: date) -> ReminderSummary:
        timezone_name = await self._shop_timezone(shop_id)
        due_transactions = await self._overdue_transactions(shop_id, as_of, timezone_name)
        candidate_customer_ids = set(due_transactions)
        active_items: list[ReminderItem] = []

        async with self.session_factory.begin() as session:
            reminders = list(
                (
                    await session.scalars(
                        select(Reminder).where(
                            Reminder.shop_id == shop_id,
                            Reminder.type == OVERDUE_TYPE,
                        )
                    )
                ).all()
            )
            reminders_by_customer = {item.customer_id: item for item in reminders}

            for customer_id, transactions in due_transactions.items():
                balance = await self.balance_service.customer_balance(shop_id, customer_id)
                reminder = reminders_by_customer.get(customer_id)
                if balance <= Decimal():
                    if reminder is not None and reminder.status == ReminderStatus.OPEN:
                        reminder.status = ReminderStatus.RESOLVED
                    continue
                due_date = min(item[0] for item in transactions)
                customer_name = transactions[0][1]
                due_at = datetime.combine(
                    due_date,
                    time.min,
                    tzinfo=self._zone(timezone_name),
                )
                if reminder is None:
                    reminder = Reminder(
                        shop_id=shop_id,
                        customer_id=customer_id,
                        type=OVERDUE_TYPE,
                        due_at=due_at,
                        status=ReminderStatus.OPEN,
                        payload={},
                    )
                    session.add(reminder)
                else:
                    reminder.status = ReminderStatus.OPEN
                    reminder.due_at = due_at
                reminder.payload = {
                    "balance": str(balance.quantize(CENT)),
                    "overdue_transaction_count": len(transactions),
                }
                active_items.append(
                    self._item(
                        customer_id=customer_id,
                        customer_name=customer_name,
                        due_at=due_at,
                        balance=balance,
                        overdue_transaction_count=len(transactions),
                        as_of=as_of,
                    )
                )

            for reminder in reminders:
                if (
                    reminder.status == ReminderStatus.OPEN
                    and reminder.customer_id not in candidate_customer_ids
                ):
                    reminder.status = ReminderStatus.RESOLVED

        return self._summary(active_items)

    async def list_open(self, shop_id: UUID) -> ReminderSummary:
        timezone_name = await self._shop_timezone(shop_id)
        as_of = datetime.now(self._zone(timezone_name)).date()
        async with self.session_factory() as session:
            rows = (
                await session.execute(
                    select(Reminder, Customer.name)
                    .join(
                        Customer,
                        and_(
                            Customer.id == Reminder.customer_id,
                            Customer.shop_id == shop_id,
                        ),
                    )
                    .where(
                        Reminder.shop_id == shop_id,
                        Reminder.type == OVERDUE_TYPE,
                        Reminder.status == ReminderStatus.OPEN,
                    )
                    .order_by(Reminder.due_at, Reminder.id)
                )
            ).all()
        items = [
            self._item(
                customer_id=reminder.customer_id,
                customer_name=customer_name,
                due_at=reminder.due_at,
                balance=Decimal(reminder.payload["balance"]),
                overdue_transaction_count=int(reminder.payload["overdue_transaction_count"]),
                as_of=as_of,
            )
            for reminder, customer_name in rows
            if reminder.customer_id is not None
        ]
        return self._summary(items)

    async def _shop_timezone(self, shop_id: UUID) -> str:
        async with self.session_factory() as session:
            timezone_name = await session.scalar(
                select(Shop.timezone).where(Shop.id == shop_id)
            )
        return timezone_name or "Asia/Shanghai"

    async def _overdue_transactions(
        self, shop_id: UUID, as_of: date, timezone_name: str
    ) -> dict[UUID, list[tuple[date, str]]]:
        zone = self._zone(timezone_name)
        async with self.session_factory() as session:
            rows = (
                await session.execute(
                    select(Transaction, Customer.name)
                    .join(
                        Customer,
                        and_(
                            Customer.id == Transaction.customer_id,
                            Customer.shop_id == shop_id,
                        ),
                    )
                    .where(
                        Transaction.shop_id == shop_id,
                        Transaction.payment_status == PaymentStatus.UNPAID,
                    )
                    .order_by(Transaction.occurred_at, Transaction.id)
                )
            ).all()
        grouped: dict[UUID, list[tuple[date, str]]] = defaultdict(list)
        for transaction, customer_name in rows:
            due_date = transaction.occurred_at.astimezone(zone).date() + timedelta(
                days=self.overdue_days
            )
            if as_of > due_date:
                grouped[transaction.customer_id].append((due_date, customer_name))
        return grouped

    @staticmethod
    def _zone(timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("Asia/Shanghai")

    @staticmethod
    def _item(
        *,
        customer_id: UUID,
        customer_name: str,
        due_at: datetime,
        balance: Decimal,
        overdue_transaction_count: int,
        as_of: date,
    ) -> ReminderItem:
        return ReminderItem(
            customer_id=customer_id,
            customer_name=customer_name,
            due_at=due_at,
            balance=balance.quantize(CENT),
            overdue_transaction_count=overdue_transaction_count,
            overdue_days=(as_of - due_at.date()).days,
        )

    @staticmethod
    def _summary(items: list[ReminderItem]) -> ReminderSummary:
        ordered = sorted(items, key=lambda item: (item.due_at, item.customer_id))
        return ReminderSummary(overdue_count=len(ordered), items=ordered)
