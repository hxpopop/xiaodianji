from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from xiaodianji.models import Anomaly, Customer, Reminder, ReminderStatus
from xiaodianji.queries.service_implementation import QueryService as _QueryService
from xiaodianji.schemas.query import QueryResponse


class QueryService(_QueryService):
    """Adds fixed, safe list projections to the deterministic query service."""

    async def _overdue(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            rows = (
                await session.execute(
                    select(Reminder, Customer.name)
                    .outerjoin(
                        Customer,
                        and_(
                            Customer.id == Reminder.customer_id,
                            Customer.shop_id == shop_id,
                        ),
                    )
                    .where(
                        Reminder.shop_id == shop_id,
                        Reminder.type == "overdue",
                        Reminder.status == ReminderStatus.OPEN,
                    )
                    .order_by(Reminder.due_at, Reminder.id)
                )
            ).all()
        details: list[dict[str, Any]] = [
            {
                "id": reminder.id,
                "customer_name": name,
                "due_at": reminder.due_at,
            }
            for reminder, name in rows
        ]
        return QueryResponse(
            answer=f"共有 {len(details)} 笔未解决逾期账目。",
            calculation_basis="未解决逾期提醒",
            details=details,
        )

    async def _anomaly(self, shop_id: UUID) -> QueryResponse:
        async with self.session_factory() as session:
            records = list(
                (
                    await session.scalars(
                        select(Anomaly)
                        .where(
                            Anomaly.shop_id == shop_id,
                            Anomaly.status == ReminderStatus.OPEN,
                        )
                        .order_by(Anomaly.created_at.desc(), Anomaly.id)
                    )
                ).all()
            )
        details: list[dict[str, Any]] = [
            {
                "id": record.id,
                "type": record.type,
                "severity": record.severity,
                "message": record.payload.get("message"),
                "created_at": record.created_at,
            }
            for record in records
        ]
        return QueryResponse(
            answer=f"共有 {len(details)} 条未解决异常。",
            calculation_basis="未解决异常记录",
            details=details,
        )
