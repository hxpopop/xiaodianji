from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.evidences.conftest import FakeObjectStorage
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Evidence, PendingConfirmation, Shop
from xiaodianji.providers.fake import FakeASRProvider, FakeExtractionProvider
from xiaodianji.records.extraction import RecordWorkflow


WAV_DATA = b"RIFF\x04\x00\x00\x00WAVEdata"


async def test_voice_record_keeps_evidence_and_attaches_transcript() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="语音记账测试店"))

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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/records/voice",
            headers={
                "X-Shop-Id": str(shop_id),
                "Idempotency-Key": "voice-001",
            },
            files={"file": ("trade.wav", WAV_DATA, "audio/wav")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["field_confidences"]["items.1.quantity"] == "0.62"
    async with factory() as session:
        evidence = await session.scalar(select(Evidence))
        confirmation = await session.scalar(select(PendingConfirmation))
    assert evidence is not None
    assert evidence.asr_text == "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"
    assert confirmation is not None
    assert confirmation.source_evidence_id == evidence.id
    await engine.dispose()
