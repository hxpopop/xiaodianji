import json
from decimal import Decimal

import httpx

from xiaodianji.providers.base import ExtractionResult, ProviderUnavailable
from xiaodianji.schemas.record import record_draft_adapter


class OpenAICompatibleExtractionProvider:
    def __init__(self, *, url: str, api_key: str, model: str, timeout_seconds: int) -> None:
        self.url, self.api_key, self.model, self.timeout_seconds = url, api_key, model, timeout_seconds

    async def extract(self, text: str) -> ExtractionResult:
        if not self.url or not self.model:
            raise ProviderUnavailable("LLM extraction provider is not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {"model": self.model, "messages": [{"role": "system", "content": "Extract only a candidate accounting RecordDraft. Do not create records or decide balances."}, {"role": "user", "content": text}], "response_format": {"type": "json_schema", "json_schema": {"name": "record_draft", "strict": True, "schema": record_draft_adapter.json_schema()}}}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            candidate = content if isinstance(content, dict) else json.loads(content)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProviderUnavailable("LLM extraction provider failed") from error
        confidences = candidate.pop("field_confidences", {})
        return ExtractionResult(draft=candidate, field_confidences={path: Decimal(str(value)) for path, value in confidences.items()}, model_name=self.model)
