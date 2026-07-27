from httpx import ASGITransport, AsyncClient

from xiaodianji.evidences.service import EvidenceService
from xiaodianji.main import create_app


WAV_DATA = b"RIFF\x04\x00\x00\x00WAVEdata"


async def test_rejects_unsupported_evidence_type(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, _ = evidence_database
    app = create_app(
        evidence_service=EvidenceService(factory, fake_storage),
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/evidences",
            headers={"X-Shop-Id": str(shop_id)},
            files={
                "file": (
                    "payload.exe",
                    b"bad",
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 415
    assert fake_storage.objects == {}


async def test_accepts_audio_and_uses_server_generated_object_key(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, _ = evidence_database
    app = create_app(
        evidence_service=EvidenceService(factory, fake_storage),
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/evidences",
            headers={"X-Shop-Id": str(shop_id)},
            files={"file": ("../../trade.wav", WAV_DATA, "audio/wav")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "audio"
    assert body["mime_type"] == "audio/wav"
    assert body["size_bytes"] == len(WAV_DATA)
    assert body["access_url"] is None
    [object_key] = fake_storage.objects
    assert object_key.startswith(f"{shop_id}/")
    assert object_key.endswith(".wav")
    assert "trade" not in object_key
    assert ".." not in object_key


async def test_rejects_file_over_configured_limit(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, _ = evidence_database
    app = create_app(
        evidence_service=EvidenceService(
            factory,
            fake_storage,
            max_size_bytes=8,
        ),
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/evidences",
            headers={"X-Shop-Id": str(shop_id)},
            files={"file": ("trade.wav", WAV_DATA, "audio/wav")},
        )

    assert response.status_code == 413
    assert fake_storage.objects == {}

