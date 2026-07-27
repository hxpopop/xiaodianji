from sqlalchemy import select

from tests.queries.test_service import _service, query_seed
from xiaodianji.models import Anomaly


async def test_anomaly_query_generates_message_without_returning_payload_text(
    query_seed,
) -> None:
    factory, shop_id, other_shop_id, _ = query_seed
    hostile_message = f"外店客户 {other_shop_id} 的凭证不应泄漏"
    async with factory.begin() as session:
        anomaly = await session.scalar(
            select(Anomaly).where(Anomaly.shop_id == shop_id)
        )
        assert anomaly is not None
        anomaly.payload = {"message": hostile_message}

    result = await _service(factory).query(shop_id, "最近有哪些异常")

    assert result.details[0]["message"] == "金额不一致"
    assert hostile_message not in str(result.details)
    assert str(other_shop_id) not in str(result.details)
