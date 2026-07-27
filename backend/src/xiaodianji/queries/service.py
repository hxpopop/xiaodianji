from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from xiaodianji.customers.service import CustomerService
from xiaodianji.models import Anomaly, Customer, Evidence, Payment, PaymentStatus, PendingConfirmation, Quote, QuoteItem, Reminder, ReminderStatus, Shop, Transaction
from xiaodianji.models.confirmation import ConfirmationStatus
from xiaodianji.queries.intents import QueryIntent
from xiaodianji.queries.parser import ParsedQuery, parse_intent
from xiaodianji.schemas.query import QueryResponse


CENT = Decimal("0.01")


def _money(value: Decimal | int | None) -> str:
    return str(Decimal(value or 0).quantize(CENT))


class QueryService:
    """A closed set of parameterized, shop-scoped financial read queries."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], customer_service: CustomerService, *, now: Callable[[], datetime] | None = None) -> None:
        self.session_factory = session_factory
        self.customer_service = customer_service
        self.now = now or (lambda: datetime.now(timezone.utc))

    async def query(self, shop_id: UUID, question: str) -> QueryResponse:
        parsed = parse_intent(question)
        if parsed.intent is None:
            return self._unsupported()
        try:
            handlers = {
                QueryIntent.CUSTOMER_BALANCE: lambda: self._balance(shop_id, parsed),
                QueryIntent.HISTORICAL_QUOTE: lambda: self._quote(shop_id, parsed),
                QueryIntent.DAILY_FLOW: lambda: self._daily(shop_id),
                QueryIntent.OVERDUE: lambda: self._overdue(shop_id),
                QueryIntent.PENDING: lambda: self._pending(shop_id),
                QueryIntent.ANOMALY: lambda: self._anomaly(shop_id),
            }
            return await handlers[parsed.intent]()
        except SQLAlchemyError:
            return QueryResponse(answer="查询暂时不可用，请稍后重试")

    @staticmethod
    def _unsupported() -> QueryResponse:
        return QueryResponse(answer="暂不支持该问题，请说得更明确一些。")

    async def _customer(self, shop_id: UUID, parsed: ParsedQuery) -> tuple[UUID | None, QueryResponse | None]:
        if not parsed.customer_name:
            return None, QueryResponse(answer="请说明要查询的客户名称。")
        match = await self.customer_service.match(shop_id, parsed.customer_name)
        if match.customer_id:
            return match.customer_id, None
        candidates = [candidate.model_dump(mode="json") for candidate in match.candidates]
        return None, QueryResponse(
            answer="客户名称存在歧义，请选择客户后再查询。" if candidates else "没有找到该客户，请检查客户名称后再查询。",
            ambiguity={"candidates": candidates},
        )

    async def _balance(self, shop_id: UUID, parsed: ParsedQuery) -> QueryResponse:
        customer_id, response = await self._customer(shop_id, parsed)
        if response:
            return response
        assert customer_id
        async with self.session_factory() as session:
            transactions = list((await session.scalars(select(Transaction).where(Transaction.shop_id == shop_id, Transaction.customer_id == customer_id, Transaction.payment_status == PaymentStatus.UNPAID).order_by(Transaction.occurred_at.desc(), Transaction.id))).all())
            payments = list((await session.scalars(select(Payment).where(Payment.shop_id == shop_id, Payment.customer_id == customer_id).order_by(Payment.paid_at.desc(), Payment.id))).all())
            evidence_ids = await self._owned_evidence_ids(session, shop_id, [x.source_evidence_id for x in transactions + payments])
        owned = set(evidence_ids)
        details: list[dict[str, Any]] = [
            {"id": x.id, "type": "transaction", "occurred_at": x.occurred_at, "amount": _money(x.total_amount), "evidence_id": x.source_evidence_id if x.source_evidence_id in owned else None}
            for x in transactions
        ] + [
            {"id": x.id, "type": "payment", "paid_at": x.paid_at, "amount": _money(x.amount), "evidence_id": x.source_evidence_id if x.source_evidence_id in owned else None}
            for x in payments
        ]
        amount = _money(sum((x.total_amount for x in transactions), Decimal()) - sum((x.amount for x in payments), Decimal()))
        return QueryResponse(answer=f"当前欠款为 {amount} 元。", amount=amount, calculation_basis="赊账交易总额 - 收款总额", details=details, evidence_ids=evidence_ids)

    async def _quote(self, shop_id: UUID, parsed: ParsedQuery) -> QueryResponse:
        customer_id, response = await self._customer(shop_id, parsed)
        if response:
            return response
        assert customer_id
        async with self.session_factory() as session:
            statement = select(Quote, QuoteItem).join(QuoteItem, QuoteItem.quote_id == Quote.id).where(Quote.shop_id == shop_id, Quote.customer_id == customer_id).order_by(Quote.quoted_at.desc(), Quote.id, QuoteItem.id)
            if parsed.product:
                statement = statement.where(QuoteItem.product.ilike(f"%{parsed.product}%"))
            rows = (await session.execute(statement)).all()
            if not rows:
                return QueryResponse(answer="没有找到符合条件的历史报价。")
            quote, item = rows[0]
            items = [line for row_quote, line in rows if row_quote.id == quote.id]
            evidence_ids = await self._owned_evidence_ids(session, shop_id, [quote.source_evidence_id])
        evidence_id = quote.source_evidence_id if quote.source_evidence_id in set(evidence_ids) else None
        amount = _money(item.subtotal if parsed.product else quote.total_amount)
        details = [{"id": line.id, "quote_id": quote.id, "product": line.product, "quantity": str(line.quantity), "unit": line.unit, "unit_price": _money(line.unit_price), "subtotal": _money(line.subtotal), "quoted_at": quote.quoted_at, "evidence_id": evidence_id} for line in items]
        return QueryResponse(answer=f"最近一次报价为 {amount} 元。", amount=amount, calculation_basis="最近一次已匹配客户的报价明细", details=details, evidence_ids=evidence_ids)

    async def _daily(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            timezone_name = await session.scalar(select(Shop.timezone).where(Shop.id == shop_id))
            try:
                local_now = self.now().astimezone(ZoneInfo(timezone_name or "Asia/Shanghai"))
            except (TypeError, ValueError, ZoneInfoNotFoundError):
                local_now = self.now().astimezone(ZoneInfo("Asia/Shanghai"))
            start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            transactions = list((await session.scalars(select(Transaction).where(Transaction.shop_id == shop_id, Transaction.occurred_at >= start, Transaction.occurred_at < end).order_by(Transaction.occurred_at, Transaction.id))).all())
            payments = list((await session.scalars(select(Payment).where(Payment.shop_id == shop_id, Payment.paid_at >= start, Payment.paid_at < end).order_by(Payment.paid_at, Payment.id))).all())
            evidence_ids = await self._owned_evidence_ids(session, shop_id, [x.source_evidence_id for x in transactions + payments])
        owned = set(evidence_ids)
        details: list[dict[str, Any]] = [
            {"id": x.id, "type": "transaction", "occurred_at": x.occurred_at, "amount": _money(x.total_amount), "evidence_id": x.source_evidence_id if x.source_evidence_id in owned else None}
            for x in transactions
        ] + [
            {"id": x.id, "type": "payment", "paid_at": x.paid_at, "amount": _money(x.amount), "evidence_id": x.source_evidence_id if x.source_evidence_id in owned else None}
            for x in payments
        ]
        amount = _money(sum((x.total_amount for x in transactions), Decimal()) + sum((x.amount for x in payments), Decimal()))
        return QueryResponse(answer=f"今天流水为 {amount} 元。", amount=amount, calculation_basis="当日交易总额 + 当日收款总额", details=details, evidence_ids=evidence_ids)

    async def _overdue(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            rows = (await session.execute(select(Reminder, Customer.name).outerjoin(Customer, and_(Customer.id == Reminder.customer_id, Customer.shop_id == shop_id)).where(Reminder.shop_id == shop_id, Reminder.type == "overdue", Reminder.status == ReminderStatus.OPEN).order_by(Reminder.due_at, Reminder.id))).all()
        details = [{"id": reminder.id, "customer_name": name, "due_at": reminder.due_at, "payload": reminder.payload} for reminder, name in rows]
        return QueryResponse(answer=f"共有 {len(details)} 笔未解决逾期账目。", calculation_basis="未解决逾期提醒", details=details)

    async def _pending(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            records = list((await session.scalars(select(PendingConfirmation).where(PendingConfirmation.shop_id == shop_id, PendingConfirmation.status == ConfirmationStatus.PENDING).order_by(PendingConfirmation.created_at, PendingConfirmation.id))).all())
            evidence_ids = await self._owned_evidence_ids(session, shop_id, [x.source_evidence_id for x in records])
        owned = set(evidence_ids)
        details = [{"id": x.id, "target_type": x.target_type, "customer_name": x.extracted_json.get("customer_name"), "created_at": x.created_at, "evidence_id": x.source_evidence_id if x.source_evidence_id in owned else None} for x in records]
        return QueryResponse(answer=f"共有 {len(details)} 条待确认记录。", calculation_basis="状态为 pending 的待确认记录", details=details, evidence_ids=evidence_ids)

    async def _anomaly(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            records = list((await session.scalars(select(Anomaly).where(Anomaly.shop_id == shop_id, Anomaly.status == ReminderStatus.OPEN).order_by(Anomaly.created_at.desc(), Anomaly.id))).all())
        details = [{"id": x.id, "type": x.type, "severity": x.severity, "message": x.payload.get("message"), "payload": x.payload, "created_at": x.created_at} for x in records]
        return QueryResponse(answer=f"共有 {len(details)} 条未解决异常。", calculation_basis="未解决异常记录", details=details)

    @staticmethod
    async def _owned_evidence_ids(session: AsyncSession, shop_id: UUID, candidates: list[UUID | None]) -> list[UUID]:
        ids = list(dict.fromkeys(x for x in candidates if x is not None))
        if not ids:
            return []
        return list((await session.scalars(select(Evidence.id).where(Evidence.shop_id == shop_id, Evidence.id.in_(ids)).order_by(Evidence.id))).all())
