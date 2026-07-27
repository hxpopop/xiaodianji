import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from xiaodianji.evaluation.runner import EvaluationRunner
from xiaodianji.models import Base, EvaluationCase, EvaluationResult, EvaluationRun, Shop
from xiaodianji.providers.base import ExtractionResult, ProviderUnavailable


TEST_DATABASE_URL = os.environ.get(
    "XDJ_TEST_DATABASE_URL",
    "postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test",
)


class ControlledPredictor:
    def __init__(self, predictions: dict[str, dict | Exception]) -> None:
        self.predictions = predictions

    async def extract(self, text: str) -> ExtractionResult:
        answer = self.predictions[text]
        if isinstance(answer, Exception):
            raise answer
        return ExtractionResult(draft=answer, field_confidences={}, model_name="controlled")


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
    shop_id, other_shop_id = uuid4(), uuid4()
    async with factory.begin() as session:
        session.add_all([Shop(id=shop_id, name="评测店"), Shop(id=other_shop_id, name="隔离店")])
    yield factory, shop_id, other_shop_id
    await engine.dispose()


def valid_transaction(product: str = "水管") -> dict:
    return {
        "target_type": "transaction", "customer_name": "星河装饰",
        "occurred_at": "2026-07-27T10:00:00+08:00", "payment_status": "unpaid",
        "items": [{"product": product, "quantity": "2", "unit": "件", "unit_price": "12.50"}],
    }


async def test_runner_persists_valid_predictions_and_controlled_provider_failures(database) -> None:
    factory, shop_id, _ = database
    predictor = ControlledPredictor({
        "成功样本": valid_transaction(),
        "失败样本": ProviderUnavailable("offline"),
    })
    runner = EvaluationRunner(factory, predictor, cases=[
        {"stable_key": "eval-runner-success", "input_type": "text", "input": {"text": "成功样本"}, "expected": valid_transaction(), "tags": ["single_product"]},
        {"stable_key": "eval-runner-failure", "input_type": "text", "input": {"text": "失败样本"}, "expected": valid_transaction(), "tags": ["provider_failure"]},
    ])

    run = await runner.run(shop_id, "controlled-v1")

    assert run.case_count == 2
    assert run.failed_case_count == 1
    assert run.metrics.customer.correct == 1
    assert run.metrics.customer.total == 2
    assert run.average_latency_ms >= 0
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(EvaluationCase)) == 2
        assert await session.scalar(select(func.count()).select_from(EvaluationResult)) == 2
        persisted = await session.scalar(select(EvaluationRun).where(EvaluationRun.id == run.id))
    assert persisted.summary_json["failed_case_count"] == 1
    assert "offline" not in str(persisted.summary_json)


async def test_runner_import_is_idempotent_and_get_is_shop_isolated(database) -> None:
    factory, shop_id, other_shop_id = database
    runner = EvaluationRunner(factory, ControlledPredictor({"成功样本": valid_transaction()}), cases=[
        {"stable_key": "eval-runner-idempotent", "input_type": "text", "input": {"text": "成功样本"}, "expected": valid_transaction(), "tags": ["single_product"]},
    ])

    first = await runner.run(shop_id, "controlled-v1")
    second = await runner.run(shop_id, "controlled-v1")

    assert first.id != second.id
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(EvaluationCase)) == 1
    assert await runner.get(shop_id, first.id) is not None
    assert await runner.get(other_shop_id, first.id) is None

async def test_runner_scores_only_the_current_fixed_case_keys(database) -> None:
    factory, shop_id, _ = database
    async with factory.begin() as session:
        session.add(EvaluationCase(
            shop_id=shop_id,
            stable_key="retired-fixed-case",
            input_type="text",
            input_payload={"text": "旧样本"},
            expected_json=valid_transaction(),
            tags=["retired"],
        ))
    runner = EvaluationRunner(factory, ControlledPredictor({"当前样本": valid_transaction()}), cases=[
        {"stable_key": "current-fixed-case", "input_type": "text", "input": {"text": "当前样本"}, "expected": valid_transaction(), "tags": ["single_product"]},
    ])

    run = await runner.run(shop_id, "controlled-v1")

    assert run.case_count == 1
    assert [result.stable_key for result in run.results] == ["current-fixed-case"]


async def test_runner_handles_an_empty_current_fixed_case_set(database) -> None:
    factory, shop_id, _ = database
    async with factory.begin() as session:
        session.add(EvaluationCase(
            shop_id=shop_id,
            stable_key="retired-fixed-case",
            input_type="text",
            input_payload={"text": "旧样本"},
            expected_json=valid_transaction(),
            tags=["retired"],
        ))
    runner = EvaluationRunner(factory, ControlledPredictor({}), cases=[])

    run = await runner.run(shop_id, "controlled-v1")

    assert run.case_count == 0
    assert run.results == []
