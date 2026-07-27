import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.evidences.conftest import FakeObjectStorage
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Evidence, PendingConfirmation, RecordCreationReservation, Shop
from xiaodianji.providers.fake import FakeASRProvider, FakeExtractionProvider
import xiaodianji.records.extraction as extraction_module
from xiaodianji.records.extraction import RecordWorkflow


WAV_DATA = b"RIFF\x04\x00\x00\x00WAVEdata"


async def test_voice_record_is_idempotent_before_upload_and_extraction() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="语音记账测试店"))

    evidence_service = EvidenceService(factory, FakeObjectStorage())
    app = create_app(evidence_service=evidence_service, record_workflow=RecordWorkflow(confirmation_workflow=SQLAlchemyLedgerWorkflow(factory), extraction_provider=FakeExtractionProvider(), asr_provider=FakeASRProvider(), evidence_service=evidence_service))
    transport = ASGITransport(app=app)
    headers = {"X-Shop-Id": str(shop_id), "Idempotency-Key": "voice-001"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/records/voice", headers=headers, files={"file": ("trade.wav", WAV_DATA, "audio/wav")})
        second = await client.post("/api/v1/records/voice", headers=headers, files={"file": ("trade.wav", WAV_DATA, "audio/wav")})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    async with factory() as session:
        evidence_count = await session.scalar(select(func.count()).select_from(Evidence))
        confirmation_count = await session.scalar(select(func.count()).select_from(PendingConfirmation))
        evidence = await session.scalar(select(Evidence))
        confirmation = await session.scalar(select(PendingConfirmation))
    assert evidence_count == 1
    assert confirmation_count == 1
    assert evidence is not None
    assert evidence.asr_text == "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"
    assert confirmation is not None
    assert confirmation.source_evidence_id == evidence.id
    await engine.dispose()


async def test_voice_record_reclaims_expired_reservation_and_completes_once() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    idempotency_key = "voice-expired-reservation"
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="过期预约测试店"))
    async with factory.begin() as session:
        session.add(
            RecordCreationReservation(
                shop_id=shop_id,
                idempotency_key=idempotency_key,
                owner_token=uuid4(),
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )

    evidence_service = EvidenceService(factory, FakeObjectStorage())
    app = create_app(
        evidence_service=evidence_service,
        record_workflow=RecordWorkflow(
            confirmation_workflow=SQLAlchemyLedgerWorkflow(factory),
            extraction_provider=FakeExtractionProvider(),
            asr_provider=FakeASRProvider(),
            evidence_service=evidence_service,
        ),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/records/voice",
            headers={"X-Shop-Id": str(shop_id), "Idempotency-Key": idempotency_key},
            files={"file": ("trade.wav", WAV_DATA, "audio/wav")},
        )

    assert response.status_code == 201
    async with factory() as session:
        evidence_count = await session.scalar(select(func.count()).select_from(Evidence))
        confirmation_count = await session.scalar(select(func.count()).select_from(PendingConfirmation))
        reservation_count = await session.scalar(select(func.count()).select_from(RecordCreationReservation))
    assert evidence_count == 1
    assert confirmation_count == 1
    assert reservation_count == 0
    await engine.dispose()


async def test_voice_record_does_not_steal_an_active_reservation() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    idempotency_key = "voice-active-reservation"
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="有效预约测试店"))
    async with factory.begin() as session:
        session.add(
            RecordCreationReservation(
                shop_id=shop_id,
                idempotency_key=idempotency_key,
                owner_token=uuid4(),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=1),
            )
        )

    evidence_service = EvidenceService(factory, FakeObjectStorage())
    app = create_app(
        evidence_service=evidence_service,
        record_workflow=RecordWorkflow(
            confirmation_workflow=SQLAlchemyLedgerWorkflow(factory),
            extraction_provider=FakeExtractionProvider(),
            asr_provider=FakeASRProvider(),
            evidence_service=evidence_service,
        ),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        request = asyncio.create_task(
            client.post(
                "/api/v1/records/voice",
                headers={"X-Shop-Id": str(shop_id), "Idempotency-Key": idempotency_key},
                files={"file": ("trade.wav", WAV_DATA, "audio/wav")},
            )
        )
        await asyncio.sleep(0.1)
        assert not request.done()
        async with factory() as session:
            evidence_count_while_reserved = await session.scalar(select(func.count()).select_from(Evidence))
        response = await asyncio.wait_for(request, timeout=2)

    assert evidence_count_while_reserved == 0
    assert response.status_code == 201
    await engine.dispose()


async def test_voice_record_surfaces_unexpected_reservation_database_error(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="数据库错误测试店"))

    def fail_reservation_insert(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        if statement.startswith("INSERT INTO record_creation_reservations"):
            raise RuntimeError("reservation database unavailable")

    async def fail_if_treated_as_contention(_delay: float) -> None:
        raise AssertionError("database failure was treated as reservation contention")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_reservation_insert)
    monkeypatch.setattr(extraction_module, "asyncio", SimpleNamespace(sleep=fail_if_treated_as_contention))
    evidence_service = EvidenceService(factory, FakeObjectStorage())
    app = create_app(
        evidence_service=evidence_service,
        record_workflow=RecordWorkflow(
            confirmation_workflow=SQLAlchemyLedgerWorkflow(factory),
            extraction_provider=FakeExtractionProvider(),
            asr_provider=FakeASRProvider(),
            evidence_service=evidence_service,
        ),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with pytest.raises(RuntimeError, match="reservation database unavailable"):
            await client.post(
                "/api/v1/records/voice",
                headers={"X-Shop-Id": str(shop_id), "Idempotency-Key": "voice-database-error"},
                files={"file": ("trade.wav", WAV_DATA, "audio/wav")},
            )
    await engine.dispose()
