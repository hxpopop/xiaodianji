import httpx

from xiaodianji.providers.base import ASRResult, ProviderUnavailable


class HTTPASRProvider:
    def __init__(self, *, url: str, api_key: str, model: str, timeout_seconds: int) -> None:
        self.url, self.api_key, self.model, self.timeout_seconds = url, api_key, model, timeout_seconds

    async def transcribe(self, audio: bytes, mime_type: str) -> ASRResult:
        if not self.url or not self.model:
            raise ProviderUnavailable("ASR provider is not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, data={"model": self.model}, files={"file": ("audio", audio, mime_type)})
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("ASR response must be a JSON object")
            transcript = payload.get("text") or payload.get("transcript")
            if not isinstance(transcript, str) or not transcript.strip():
                raise ValueError("ASR response did not include a transcript")
        except (httpx.HTTPError, AttributeError, TypeError, ValueError) as error:
            raise ProviderUnavailable("ASR provider failed") from error
        return ASRResult(transcript=transcript.strip(), model_name=self.model)
