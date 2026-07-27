from httpx import ASGITransport, AsyncClient

from xiaodianji.evidences.service import EvidenceService
from xiaodianji.main import create_app


WAV_DATA = b"RIFF\x04\x00\x00\x00WAVEdata"


async def test_access_returns_five_minute_signed_url_and_is_tenant_scoped(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, other_shop_id = evidence_database
    service = EvidenceService(factory, fake_storage)
    evidence = await service.create_upload(
        shop_id=shop_id,
        original_filename="trade.wav",
        mime_type="audio/wav",
        data=WAV_DATA,
    )
    app = create_app(evidence_service=service)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        found = await client.get(
            f"/api/v1/evidences/{evidence.id}",
            headers={"X-Shop-Id": str(shop_id)},
        )
        hidden = await client.get(
            f"/api/v1/evidences/{evidence.id}",
            headers={"X-Shop-Id": str(other_shop_id)},
        )

    assert found.status_code == 200
    assert found.json()["access_url"].endswith("?expires=300")
    assert fake_storage.presign_calls[-1][1] == 300
    assert hidden.status_code == 404


async def test_transcript_is_attached_only_within_owning_shop(
    evidence_database,
    fake_storage,
) -> None:
    factory, shop_id, other_shop_id = evidence_database
    service = EvidenceService(factory, fake_storage)
    evidence = await service.create_upload(
        shop_id=shop_id,
        original_filename="trade.wav",
        mime_type="audio/wav",
        data=WAV_DATA,
    )

    updated = await service.attach_transcript(
        shop_id,
        evidence.id,
        "王老板拿了十个插座",
    )

    assert updated.asr_text == "王老板拿了十个插座"
    app = create_app(evidence_service=service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        hidden = await client.get(
            f"/api/v1/evidences/{evidence.id}",
            headers={"X-Shop-Id": str(other_shop_id)},
        )
    assert hidden.status_code == 404

