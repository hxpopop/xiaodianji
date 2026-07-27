from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="XDJ_",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://xiaodianji:xiaodianji@localhost:5432/xiaodianji"
    )
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    object_storage_bucket: str = "evidences"
    confidence_threshold: Decimal = Field(
        default=Decimal("0.75"),
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    timezone: str = "Asia/Shanghai"
    llm_provider: str = "fake"
    llm_api_key: str = ""
    asr_provider: str = "fake"
    asr_api_key: str = ""

