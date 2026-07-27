from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.evidences.conftest import FakeObjectStorage
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Evidence, PendingConfirmation, Shop
from xiaodianji.providers.fake import FakeASRProvider, FakeExtractionProvider
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
