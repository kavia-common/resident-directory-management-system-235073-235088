from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables are expected to be configured by the orchestrator/platform.

    Security note:
        `JWT_SECRET` is required in production. For local development / sandbox integration only,
        you may set `ALLOW_INSECURE_DEV_JWT=1` to permit a fixed fallback secret.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_allow_origins: List[str] = Field(default=["*"], description="Allowed CORS origins.")
    postgres_url: Optional[str] = Field(default=None, description="Full Postgres connection URL.")
    postgres_user: Optional[str] = Field(default=None, description="Postgres user.")
    postgres_password: Optional[str] = Field(default=None, description="Postgres password.")
    postgres_db: Optional[str] = Field(default=None, description="Postgres database name.")
    postgres_port: Optional[str] = Field(default=None, description="Postgres port.")

    # If true, allows using a fixed insecure dev JWT secret when JWT_SECRET is not set.
    allow_insecure_dev_jwt: bool = Field(
        default=False,
        description="DEV ONLY: allow a fixed fallback JWT secret if JWT_SECRET is missing.",
        validation_alias="ALLOW_INSECURE_DEV_JWT",
    )

    jwt_secret: Optional[str] = Field(default=None, description="Secret key for signing JWTs.")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(default=120, description="Access token lifetime in minutes.")

    def model_post_init(self, __context) -> None:
        # Enforce JWT secret unless explicitly allowed for dev.
        if self.jwt_secret:
            return
        if self.allow_insecure_dev_jwt:
            # Fixed, insecure secret. This is ONLY to prevent boot-time failure in sandbox/dev.
            self.jwt_secret = "insecure-dev-jwt-secret-change-me"
            return
        raise ValueError("JWT_SECRET is required (or set ALLOW_INSECURE_DEV_JWT=1 for dev only).")


_settings: Optional[Settings] = None


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
