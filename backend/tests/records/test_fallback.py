from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from xiaodianji.evidences.service import TranscriptInvalid
from xiaodianji.main import create_app
from xiaodianji.providers.base import ASRResult, ExtractionResult, ProviderUnavailable
from xiaodianji.providers.fake import FakeExtractionProvider
from xiaodianji.records.extraction import RecordWorkflow


class FailingExtractionProvider:
    async def extract(self, text: str): raise ProviderUnavailable("provider is unavailable")


class FailingASRProvider:
    async def transcribe(self, audio: bytes, mime_type: str): raise ProviderUnavailable("ASR is unavailable")


class OverlongASRProvider:
    async def transcribe(self, audio: bytes, mime_type: str): return ASRResult(transcript="x" * 50_001)


class InvalidDraftExtractionProvider:
    async def extract(self, text: str): return ExtractionResult(draft={"target_type": "transaction"}, field_confidences={})


class InvalidConfidenceExtractionProvider:
    async def extract(self, text: str):
        result = await FakeExtractionProvider().extract(text)
        return ExtractionResult(draft=result.draft, field_confidences={"items.1.quantity": "invalid"})


class NeverCreatesConfirmation:
    def __init__(self) -> None: self.calls = 0
    async def create(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("provider failure must not create a confirmation")


class RetainedEvidenceService:
    def __init__(self, *, reject_transcript: bool = False) -> None:
        self.created = 0
        self.reject_transcript = reject_transcript
    async def create_upload(self, **kwargs):
        self.created += 1
        return type("Evidence", (), {"id": uuid4(), "mime_type": kwargs["mime_type"]})()
    async def attach_transcript(self, *args, **kwargs):
        if self.reject_transcript:
            raise TranscriptInvalid("transcript is blank or too long")
        raise AssertionError("a failed ASR call must not attach a transcript")


async def post_text(extraction_provider):
    creator = NeverCreatesConfirmation()
    app = create_app(record_workflow=RecordWorkflow(confirmation_workflow=creator, extraction_provider=extraction_provider, asr_provider=FailingASRProvider()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/records/text", headers={"X-Shop-Id": str(uuid4()), "Idempotency-Key": "text-fail-001"}, json={"text": "王老板拿了一批插座"})
    return response, creator


async def test_provider_failure_returns_manual_fallback_without_record() -> None:
    response, creator = await post_text(FailingExtractionProvider())
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
    assert creator.calls == 0


async def test_invalid_extraction_draft_returns_manual_fallback_without_record() -> None:
    response, creator = await post_text(InvalidDraftExtractionProvider())
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
    assert creator.calls == 0


async def test_invalid_extraction_confidence_returns_manual_fallback_without_record() -> None:
    response, creator = await post_text(InvalidConfidenceExtractionProvider())
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
    assert creator.calls == 0


async def test_asr_failure_returns_manual_fallback_and_keeps_uploaded_evidence() -> None:
    creator, evidence_service = NeverCreatesConfirmation(), RetainedEvidenceService()
    app = create_app(record_workflow=RecordWorkflow(confirmation_workflow=creator, extraction_provider=FailingExtractionProvider(), asr_provider=FailingASRProvider(), evidence_service=evidence_service))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/records/voice", headers={"X-Shop-Id": str(uuid4()), "Idempotency-Key": "voice-fail-001"}, files={"file": ("trade.wav", b"RIFF\x04\x00\x00\x00WAVEdata", "audio/wav")})
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
    assert evidence_service.created == 1
    assert creator.calls == 0


async def test_overlong_transcript_returns_manual_fallback_without_record() -> None:
    creator, evidence_service = NeverCreatesConfirmation(), RetainedEvidenceService(reject_transcript=True)
    app = create_app(record_workflow=RecordWorkflow(confirmation_workflow=creator, extraction_provider=FakeExtractionProvider(), asr_provider=OverlongASRProvider(), evidence_service=evidence_service))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/records/voice", headers={"X-Shop-Id": str(uuid4()), "Idempotency-Key": "voice-overlong-001"}, files={"file": ("trade.wav", b"RIFF\x04\x00\x00\x00WAVEdata", "audio/wav")})
    assert response.status_code == 503
    assert response.json()["fallback"] == "manual_form"
    assert evidence_service.created == 1
    assert creator.calls == 0
