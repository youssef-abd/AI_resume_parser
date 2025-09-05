from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load from .env automatically (project root)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    database_url: str = Field(
        default="",
        description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/dbname",
        validation_alias="DATABASE_URL",
    )

    # App
    debug: bool = Field(default=False, validation_alias="DEBUG")
    model_name: str = Field(default="all-MiniLM-L6-v2", validation_alias="MODEL_NAME")
    max_upload_mb: int = Field(default=10, validation_alias="MAX_UPLOAD_MB")

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


# Optional helper for other modules
class PublicConfig(BaseModel):
    debug: bool
    model_name: str
    max_upload_mb: int
    cors_origins: List[str]


def get_public_config() -> PublicConfig:
    s = get_settings()
    return PublicConfig(
        debug=s.debug,
        model_name=s.model_name,
        max_upload_mb=s.max_upload_mb,
        cors_origins=s.cors_origins,
    )
