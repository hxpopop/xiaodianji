from httpx import ASGITransport, AsyncClient

from xiaodianji.main import create_app


async def test_health_returns_service_status() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "xiaodianji"}

