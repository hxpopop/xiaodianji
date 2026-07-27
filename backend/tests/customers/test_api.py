from uuid import UUID

from httpx import ASGITransport, AsyncClient

from xiaodianji.main import create_app


SHOP_ID = UUID("00000000-0000-0000-0000-000000000001")
CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000101")


class StubCustomerService:
    async def list_summaries(self, shop_id: UUID) -> list[dict]:
        assert shop_id == SHOP_ID
        return [
            {
                "id": CUSTOMER_ID,
                "name": "王建材",
                "aliases": ["王老板", "老王"],
            }
        ]


async def test_customer_list_returns_names_and_aliases() -> None:
    app = create_app(customer_service=StubCustomerService())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/customers",
            headers={"X-Shop-Id": str(SHOP_ID)},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(CUSTOMER_ID),
            "name": "王建材",
            "aliases": ["王老板", "老王"],
        }
    ]


async def test_customer_list_rejects_invalid_shop_id() -> None:
    app = create_app(customer_service=StubCustomerService())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/customers",
            headers={"X-Shop-Id": "not-a-uuid"},
        )

    assert response.status_code == 422
