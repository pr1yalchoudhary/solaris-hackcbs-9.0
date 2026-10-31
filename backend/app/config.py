from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:5173"]
    mongodb_uri: SecretStr = SecretStr("")
    mongodb_database: str = "solaris"
    auth_issuer: str = ""
    auth_public_key: str = ""
    auth_authorized_parties: list[str] = ["http://localhost:5173"]
    gemini_api_key: SecretStr = SecretStr("")
    enable_paid_api_calls: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
