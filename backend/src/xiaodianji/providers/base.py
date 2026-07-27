from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


class ProviderUnavailable(RuntimeError):
    """A configured ASR or extraction provider could not serve a request."""


@dataclass(frozen=True, slots=True)
class ASRResult:
    transcript: str
    model_name: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    draft: dict[str, Any]
    field_confidences: dict[str, Decimal]
    model_name: str | None = None
    schema_version: str = "1"


class ASRProvider(Protocol):
    async def transcribe(self, audio: bytes, mime_type: str) -> ASRResult: ...


class ExtractionProvider(Protocol):
    async def extract(self, text: str) -> ExtractionResult: ...
