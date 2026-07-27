from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.evidences.conftest import FakeObjectStorage
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.main import create_app
from xiaodianji.models import Base, Evidence, RecordCreationReservation, Shop
from xiaodianji.providers.base import ASRResult
from xiaodianji.providers.fake import FakeExtractionProvider
from xiaodianji.records.extraction import RecordWorkflow
from xiaodianji.schemas.record import record_draft_adapter


WAV_DATA = b"RIFF\x04\x00\x00\x00WAVEdata"


class _StaleFirstReadSession:
    def __init__(self, session, factory) -> None:
        self._session = session
        self._factory = factory

    async def scalar(self, statement):
        if self._factory.hide_first_read:
            self._factory.hide_first_read = False
            return None
        return await self._session.scalar(statement)


class _StaleFirstReadContext:
    def __init__(self, factory) -> None:
        self._factory = factory
        self._context = None

    async def __aenter__(self):
        self._context = self._factory.delegate()
        session = await self._context.__aenter__()
        return _StaleFirstReadSession(session, self._factory)

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self._context.__aexit__(exc_type, exc_value, traceback)


class StaleFirstReadFactory:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.hide_first_read = True

    def __call__(self):
        return _StaleFirstReadContext(self)

    def begin(self):
        return self.delegate.begin()


class CountingASRProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def transcribe(self, audio: bytes, mime_type: str) -> ASRResult:
        self.calls += 1
        return ASRResult(
            transcript="王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着",
            model_name="counting-asr",
        )


async def test_reserved_voice_rechecks_confirmation_after_acquiring_lease() -> None:
    engine = create_async_engine("postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shop_id = uuid4()
    idempotency_key = "voice-post-acquire-recheck"
    async with factory.begin() as session:
        session.add(Shop(id=shop_id, name="预约后复查测试店"))

    ledger_workflow = SQLAlchemyLedgerWorkflow(factory)
    extraction = await FakeExtractionProvider().extract("existing confirmation")
    draft = record_draft_adapter.validate_python(extraction.draft)
    existing = await ledger_workflow.create(shop_id, draft, idempotency_key)
    ledger_workflow.session_factory = StaleFirstReadFactory(factory)

    asr_provider = CountingASRProvider()
    storage = FakeObjectStorage()
    evidence_service = EvidenceService(factory, storage)
    app = create_app(
        evidence_service=evidence_service,
        record_workflow=RecordWorkflow(
            confirmation_workflow=ledger_workflow,
            extraction_provider=FakeExtractionProvider(),
            asr_provider=asr_provider,
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
    assert response.json()["id"] == str(existing.id)
    assert asr_provider.calls == 0
    assert storage.objects == {}
    async with factory() as session:
        evidence_count = await session.scalar(select(func.count()).select_from(Evidence))
        reservation_count = await session.scalar(select(func.count()).select_from(RecordCreationReservation))
    assert evidence_count == 0
    assert reservation_count == 0
    await engine.dispose()
