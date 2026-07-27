from sqlalchemy import select

from tests.queries.test_service import _service, query_seed
from xiaodianji.models import Evidence, Payment


async def test_balance_detail_hides_foreign_shop_evidence_id(query_seed) -> None:
    factory, shop_id, other_shop_id, _ = query_seed
    async with factory.begin() as session:
        payment = await session.scalar(
            select(Payment).where(Payment.shop_id == shop_id)
        )
        foreign_evidence_id = await session.scalar(
            select(Evidence.id).where(Evidence.shop_id == other_shop_id)
        )
        assert payment is not None
        assert foreign_evidence_id is not None
        payment.source_evidence_id = foreign_evidence_id

    result = await _service(factory).query(shop_id, "李老板还欠多少钱")

    assert foreign_evidence_id not in result.evidence_ids
    assert all(
        detail.get("evidence_id") != foreign_evidence_id
        for detail in result.details
    )
