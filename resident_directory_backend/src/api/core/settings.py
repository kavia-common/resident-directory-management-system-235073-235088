from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables are expected to be configured by the orchestrator/platform.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_allow_origins: List[str] = Field(default=["*"], description="Allowed CORS origins.")
    postgres_url: Optional[str] = Field(default=None, description="Full Postgres connection URL.")
    postgres_user: Optional[str] = Field(default=None, description="Postgres user.")
    postgres_password: Optional[str] = Field(default=None, description="Postgres password.")
    postgres_db: Optional[str] = Field(default=None, description="Postgres database name.")
    postgres_port: Optional[str] = Field(default=None, description="Postgres port.")

    jwt_secret: str = Field(..., description="Secret key for signing JWTs.")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(default=120, description="Access token lifetime in minutes.")


_settings: Optional[Settings] = None


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
