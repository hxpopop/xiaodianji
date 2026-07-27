from decimal import Decimal

import httpx
import pytest

from xiaodianji.providers.base import ProviderUnavailable
from xiaodianji.providers.fake import FakeExtractionProvider
from xiaodianji.providers.http_asr import HTTPASRProvider


async def test_fake_provider_returns_fixed_two_item_candidate() -> None:
    result = await FakeExtractionProvider().extract("王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着")

    assert result.draft["customer_name"] == "王老板"
    assert len(result.draft["items"]) == 2
    assert result.field_confidences["items.1.quantity"] == Decimal("0.62")


class MalformedASRResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return ["not", "an", "object"]


class MalformedASRClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def post(self, *args, **kwargs):
        return MalformedASRResponse()


async def test_http_asr_normalizes_non_object_json_to_provider_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MalformedASRClient)
    provider = HTTPASRProvider(url="https://asr.test", api_key="", model="asr", timeout_seconds=1)

    with pytest.raises(ProviderUnavailable):
        await provider.transcribe(b"audio", "audio/wav")
