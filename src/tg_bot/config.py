from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr
    bot_mode: Literal["mock", "onec"] = "mock"
    onec_base_url: str = "http://localhost/tg_project/hs/issue-api/v1"
    onec_api_token: SecretStr = Field(default=SecretStr(""))
    onec_timeout_seconds: float = Field(default=10, gt=0, le=60)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
