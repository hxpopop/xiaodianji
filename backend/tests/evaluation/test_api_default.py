from httpx import ASGITransport, AsyncClient

from tests.evaluation.test_api import FakeEvaluationRunner, SHOP_ONE
from xiaodianji.main import create_app


async def test_evaluation_run_uses_configured_model_when_request_has_no_body() -> None:
    app = create_app(evaluation_runner=FakeEvaluationRunner())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/evaluations/run", headers={"X-Shop-Id": str(SHOP_ONE)})

    assert response.status_code == 201
    assert response.json()["model_name"] == "configured"
