from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from xiaodianji.main import create_app
from xiaodianji.schemas.evaluation import (
    ConfirmationRate, ConfirmationRates, EvaluationMetrics, EvaluationRunRead, Score,
)


SHOP_ONE = UUID("00000000-0000-0000-0000-000000000101")
SHOP_TWO = UUID("00000000-0000-0000-0000-000000000102")


class FakeEvaluationRunner:
    def __init__(self) -> None:
        self.runs: dict[UUID, EvaluationRunRead] = {}

    async def run(self, shop_id: UUID, model_name: str) -> EvaluationRunRead:
        score = Score(correct=1, total=1, accuracy=Decimal("1.0000"))
        run = EvaluationRunRead(
            id=uuid4(), shop_id=shop_id, model_name=model_name,
            started_at=datetime.now(timezone.utc).isoformat(), finished_at=datetime.now(timezone.utc).isoformat(),
            metrics=EvaluationMetrics(customer=score, products=score, quantities=score, amounts=score, payment_status=score, case_count=1),
            confirmation_rates=ConfirmationRates(direct=ConfirmationRate.from_counts(0, 0), edited=ConfirmationRate.from_counts(0, 0), cancelled=ConfirmationRate.from_counts(0, 0), total=0),
            case_count=1, failed_case_count=0, average_latency_ms=Decimal("1.0000"),
        )
        self.runs[run.id] = run
        return run

    async def get(self, shop_id: UUID, run_id: UUID):
        run = self.runs.get(run_id)
        return run if run and run.shop_id == shop_id else None


async def test_evaluation_api_runs_fixed_cases_and_hides_other_shop_runs() -> None:
    runner = FakeEvaluationRunner()
    app = create_app(evaluation_runner=runner)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/evaluations/run", headers={"X-Shop-Id": str(SHOP_ONE)}, json={"model_name": "controlled"})
        run_id = created.json()["id"]
        found = await client.get(f"/api/v1/evaluations/{run_id}", headers={"X-Shop-Id": str(SHOP_ONE)})
        hidden = await client.get(f"/api/v1/evaluations/{run_id}", headers={"X-Shop-Id": str(SHOP_TWO)})

    assert created.status_code == 201
    assert found.status_code == 200
    assert hidden.status_code == 404
    assert created.json()["metrics"]["customer"] == {"correct": 1, "total": 1, "accuracy": "1.0000"}
