from httpx import ASGITransport, AsyncClient

from xiaodianji.evidences.service import EvidenceService
from xiaodianji.main import create_app


async def test_oversized_request_is_rejected_before_multipart_parsing(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, _ = evidence_database
    app = create_app(
        evidence_service=EvidenceService(factory, fake_storage),
        max_request_body_bytes=1024,
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/evidences",
            headers={
                "X-Shop-Id": str(shop_id),
                "Content-Length": "2048",
            },
            files={
                "file": (
                    "trade.wav",
                    b"RIFF\x04\x00\x00\x00WAVEdata",
                    "audio/wav",
                )
            },
        )

    assert response.status_code == 413
    assert fake_storage.objects == {}

