import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.evidences.conftest import FakeObjectStorage
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Shop
from xiaodianji.providers.base import ASRResult
from xiaodianji.providers.fake import FakeExtractionProvider
from xiaodianji.records.extraction import RecordWorkflow


class SlowASRProvider:
    async def transcribe(self, audio: bytes, mime_type: str) -> ASRResult:
        await asyncio.sleep(0.05)
        return ASRResult(transcript="王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着")


async def test_distinct_voice_keys_complete_with_single_connection_pool() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test", pool_size=1, max_overflow=0, pool_timeout=0.2)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="并发语音测试店"))
    evidence_service = EvidenceService(factory, FakeObjectStorage())
    app = create_app(evidence_service=evidence_service, record_workflow=RecordWorkflow(confirmation_workflow=SQLAlchemyLedgerWorkflow(factory), extraction_provider=FakeExtractionProvider(), asr_provider=SlowASRProvider(), evidence_service=evidence_service))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(*[client.post("/api/v1/records/voice", headers={"X-Shop-Id": str(shop_id), "Idempotency-Key": f"voice-concurrent-{index}"}, files={"file": ("trade.wav", b"RIFF\x04\x00\x00\x00WAVEdata", "audio/wav")}) for index in range(3)])
    assert [response.status_code for response in responses] == [201, 201, 201]
    await engine.dispose()
