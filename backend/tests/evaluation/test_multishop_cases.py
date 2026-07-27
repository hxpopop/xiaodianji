from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.evaluation.runner import EvaluationRunner
from xiaodianji.models import Base, EvaluationCase, Shop
from xiaodianji.providers.base import ExtractionResult


class SamePredictionProvider:
    async def extract(self, _text: str) -> ExtractionResult:
        return ExtractionResult(
            draft={
                "target_type": "transaction", "customer_name": "星河装饰",
                "occurred_at": "2026-07-27T09:00:00+08:00", "payment_status": "unpaid",
                "items": [{"product": "水管", "quantity": "1", "unit": "件", "unit_price": "1.00"}],
            },
            field_confidences={},
        )


async def test_two_shops_import_the_same_stable_key_without_sharing_case_rows() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    first_shop, second_shop = uuid4(), uuid4()
    async with factory.begin() as session:
        session.add_all([Shop(id=first_shop, name="甲店"), Shop(id=second_shop, name="乙店")])
    runner = EvaluationRunner(factory, SamePredictionProvider(), cases=[{
        "stable_key": "shared-fixed-case", "input_type": "text", "input": {"text": "样本"},
        "expected": {
            "target_type": "transaction", "customer_name": "星河装饰",
            "occurred_at": "2026-07-27T09:00:00+08:00", "payment_status": "unpaid",
            "items": [{"product": "水管", "quantity": "1", "unit": "件", "unit_price": "1.00"}],
        }, "tags": ["single_product"],
    }])
    try:
        first = await runner.run(first_shop, "controlled")
        second = await runner.run(second_shop, "controlled")
        async with factory() as session:
            case_count = await session.scalar(select(func.count()).select_from(EvaluationCase))
        assert first.case_count == second.case_count == 1
        assert case_count == 2
    finally:
        await engine.dispose()
