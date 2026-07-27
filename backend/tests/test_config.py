from decimal import Decimal

from xiaodianji.config import Settings


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.confidence_threshold == Decimal("0.75")
    assert settings.timezone == "Asia/Shanghai"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.llm_api_key == ""
    assert settings.asr_api_key == ""
