from sqlalchemy import select

from tests.queries.test_service import _service, query_seed
from xiaodianji.models import Anomaly, Reminder


async def test_list_queries_do_not_return_untrusted_reminder_or_anomaly_payloads(
    query_seed,
) -> None:
    factory, shop_id, other_shop_id, _ = query_seed
    async with factory.begin() as session:
        reminder = await session.scalar(
            select(Reminder).where(Reminder.shop_id == shop_id)
        )
        anomaly = await session.scalar(
            select(Anomaly).where(Anomaly.shop_id == shop_id)
        )
        assert reminder is not None
        assert anomaly is not None
        reminder.payload = {
            "foreign_shop_id": str(other_shop_id),
            "foreign_customer_name": "不应泄漏",
        }
        anomaly.payload = {
            "foreign_shop_id": str(other_shop_id),
            "foreign_evidence_id": "not-visible",
            "message": "金额不一致",
        }

    service = _service(factory)
    overdue = await service.query(shop_id, "哪些账逾期了")
    anomaly = await service.query(shop_id, "最近有哪些异常")

    assert "payload" not in overdue.details[0]
    assert "payload" not in anomaly.details[0]
    assert str(other_shop_id) not in str(overdue.details)
    assert str(other_shop_id) not in str(anomaly.details)
