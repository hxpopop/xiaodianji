from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from xiaodianji.confirmations.service import (
    ConfirmationEventRecord,
    ConfirmationRecord,
    ConfirmationService,
    FormalRecordRef,
)
from xiaodianji.main import create_app
from xiaodianji.records.manual import ManualRecordService


SHOP_ID = UUID("00000000-0000-0000-0000-000000000001")


class InMemoryConfirmationRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, ConfirmationRecord] = {}
        self.events: list[ConfirmationEventRecord] = []

    async def find_by_creation_key(self, shop_id, idempotency_key):
        return next(
            (
                record
                for record in self.records.values()
                if record.shop_id == shop_id
                and record.creation_idempotency_key == idempotency_key
            ),
            None,
        )

    async def add(self, record):
        self.records[record.id] = record
        return record

    async def get(self, confirmation_id):
        return self.records.get(confirmation_id)

    async def save(self, record):
        self.records[record.id] = record
        return record

    async def add_event(self, event):
        self.events.append(event)
        return event


class FakeFormalWriter:
    async def write(self, record: ConfirmationRecord) -> FormalRecordRef:
        return FormalRecordRef(record_type=record.target_type, record_id=uuid4())


def build_app():
    repository = InMemoryConfirmationRepository()
    return create_app(
        manual_record_service=ManualRecordService(repository),
        confirmation_service=ConfirmationService(repository, FakeFormalWriter()),
    )


async def test_manual_record_endpoint_returns_pending_card() -> None:
    transport = ASGITransport(app=build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/records/manual",
            headers={
                "X-Shop-Id": str(SHOP_ID),
                "Idempotency-Key": "manual-api-001",
            },
            json={
                "target_type": "transaction",
                "customer_name": "王老板",
                "occurred_at": "2026-07-27T10:00:00+08:00",
                "payment_status": "unpaid",
                "items": [
                    {
                        "product": "插座",
                        "quantity": "10",
                        "unit": "个",
                        "unit_price": "12",
                    }
                ],
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["effective_json"]["total_amount"] == "120.00"
    assert set(body["field_confidences"].values()) == {"1.00"}


async def test_edit_and_confirm_endpoints_return_edited_status() -> None:
    transport = ASGITransport(app=build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/v1/records/manual",
            headers={
                "X-Shop-Id": str(SHOP_ID),
                "Idempotency-Key": "manual-api-002",
            },
            json={
                "target_type": "payment",
                "customer_name": "王老板",
                "paid_at": "2026-07-27T10:00:00+08:00",
                "amount": "200",
            },
        )
        confirmation_id = created.json()["id"]
        await client.patch(
            f"/api/v1/confirmations/{confirmation_id}",
            json={
                "target_type": "payment",
                "customer_name": "王老板",
                "paid_at": "2026-07-27T10:00:00+08:00",
                "amount": "220",
            },
        )
        confirmed = await client.post(
            f"/api/v1/confirmations/{confirmation_id}/confirm",
            headers={"Idempotency-Key": "confirm-api-001"},
        )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed_after_edit"
    assert confirmed.json()["effective_json"]["amount"] == "220.00"

