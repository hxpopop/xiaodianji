from xiaodianji.config import Settings
from xiaodianji.providers.fake import FakeASRProvider, FakeExtractionProvider
from xiaodianji.providers.http_asr import HTTPASRProvider
from xiaodianji.providers.openai_compatible import OpenAICompatibleExtractionProvider


def extraction_provider_from(settings: Settings):
    if settings.llm_provider == "fake":
        return FakeExtractionProvider()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleExtractionProvider(url=settings.llm_url, api_key=settings.llm_api_key, model=settings.llm_model, timeout_seconds=settings.llm_timeout_seconds)
    raise ValueError(f"unsupported LLM provider: {settings.llm_provider}")


def asr_provider_from(settings: Settings):
    if settings.asr_provider == "fake":
        return FakeASRProvider()
    if settings.asr_provider == "http":
        return HTTPASRProvider(url=settings.asr_url, api_key=settings.asr_api_key, model=settings.asr_model, timeout_seconds=settings.asr_timeout_seconds)
    raise ValueError(f"unsupported ASR provider: {settings.asr_provider}")
