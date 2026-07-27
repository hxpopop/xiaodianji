from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from xiaodianji.confirmations.service import (
    ConfirmationConflict,
    ConfirmationEventRecord,
    ConfirmationRecord,
    ConfirmationService,
    FormalRecordRef,
)
from xiaodianji.models import ConfirmationStatus
from xiaodianji.records.manual import ManualRecordService
from xiaodianji.schemas.record import TransactionDraft


class InMemoryConfirmationRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, ConfirmationRecord] = {}
        self.events: list[ConfirmationEventRecord] = []

    async def find_by_creation_key(
        self,
        shop_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord | None:
        return next(
            (
                record
                for record in self.records.values()
                if record.shop_id == shop_id
                and record.creation_idempotency_key == idempotency_key
            ),
            None,
        )

    async def add(self, record: ConfirmationRecord) -> ConfirmationRecord:
        self.records[record.id] = record
        return record

    async def get(self, confirmation_id: UUID) -> ConfirmationRecord | None:
        return self.records.get(confirmation_id)

    async def save(self, record: ConfirmationRecord) -> ConfirmationRecord:
        self.records[record.id] = record
        return record

    async def add_event(
        self,
        event: ConfirmationEventRecord,
    ) -> ConfirmationEventRecord:
        self.events.append(event)
        return event


class FakeFormalWriter:
    def __init__(self) -> None:
        self.calls = 0

    async def write(self, record: ConfirmationRecord) -> FormalRecordRef:
        self.calls += 1
        return FormalRecordRef(record_type=record.target_type, record_id=uuid4())


def transaction_draft() -> TransactionDraft:
    return TransactionDraft.model_validate(
        {
            "target_type": "transaction",
            "customer_name": "王老板",
            "occurred_at": "2026-07-27T10:00:00+08:00",
            "payment_status": "unpaid",
            "items": [
                {
                    "product": "插座",
                    "quantity": "9",
                    "unit": "个",
                    "unit_price": "12.00",
                }
            ],
        }
    )


async def test_manual_record_is_idempotent_and_all_fields_are_certain() -> None:
    repository = InMemoryConfirmationRepository()
    service = ManualRecordService(repository)
    shop_id = uuid4()

    first = await service.create(shop_id, transaction_draft(), "manual-001")
    second = await service.create(shop_id, transaction_draft(), "manual-001")

    assert second.id == first.id
    assert first.status is ConfirmationStatus.PENDING
    assert first.field_confidences
    assert set(first.field_confidences.values()) == {"1.00"}


async def test_direct_confirmation_records_direct_status() -> None:
    repository = InMemoryConfirmationRepository()
    writer = FakeFormalWriter()
    manual_service = ManualRecordService(repository)
    confirmation_service = ConfirmationService(repository, writer)
    pending = await manual_service.create(uuid4(), transaction_draft(), "manual-002")

    result = await confirmation_service.confirm(pending.id, "confirm-001")

    assert result.status is ConfirmationStatus.CONFIRMED
    assert result.formal_record_type == "transaction"
    assert writer.calls == 1


async def test_edit_then_confirm_records_before_and_after() -> None:
    repository = InMemoryConfirmationRepository()
    writer = FakeFormalWriter()
    manual_service = ManualRecordService(repository)
    confirmation_service = ConfirmationService(repository, writer)
    pending = await manual_service.create(uuid4(), transaction_draft(), "manual-003")
    edited = deepcopy(pending.extracted_json)
    edited["items"][0]["quantity"] = "10"

    await confirmation_service.update_draft(pending.id, edited)
    result = await confirmation_service.confirm(pending.id, "confirm-002")

    assert result.status is ConfirmationStatus.CONFIRMED_AFTER_EDIT
    assert result.effective_json["total_amount"] == "120.00"
    edit_event = next(event for event in repository.events if event.event_type == "edited")
    assert edit_event.before_json["items"][0]["quantity"] == "9"
    assert edit_event.after_json["items"][0]["quantity"] == "10"


async def test_same_confirmation_key_is_idempotent_but_new_key_conflicts() -> None:
    repository = InMemoryConfirmationRepository()
    writer = FakeFormalWriter()
    manual_service = ManualRecordService(repository)
    confirmation_service = ConfirmationService(repository, writer)
    pending = await manual_service.create(uuid4(), transaction_draft(), "manual-004")

    first = await confirmation_service.confirm(pending.id, "confirm-003")
    second = await confirmation_service.confirm(pending.id, "confirm-003")

    assert second.formal_record_id == first.formal_record_id
    assert writer.calls == 1
    with pytest.raises(ConfirmationConflict):
        await confirmation_service.confirm(pending.id, "confirm-different")


async def test_cancel_is_a_terminal_audited_state() -> None:
    repository = InMemoryConfirmationRepository()
    writer = FakeFormalWriter()
    manual_service = ManualRecordService(repository)
    confirmation_service = ConfirmationService(repository, writer)
    pending = await manual_service.create(uuid4(), transaction_draft(), "manual-005")

    result = await confirmation_service.cancel(pending.id, "cancel-001")

    assert result.status is ConfirmationStatus.CANCELLED
    assert repository.events[-1].event_type == "cancelled"
    assert writer.calls == 0

