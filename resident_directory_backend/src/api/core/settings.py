from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables are expected to be configured by the orchestrator/platform.

    CORS note:
        The frontend runs in a browser and will enforce CORS. When `allow_credentials=True`
        (we use it to support Authorization headers and future cookie-based auth),
        browsers will reject wildcard origins (`*`). Therefore we default to a safe
        localhost origin and allow override via env vars.

    Security note:
        `JWT_SECRET` is required in production. For local development / sandbox integration only,
        you may set `ALLOW_INSECURE_DEV_JWT=1` to permit a fixed fallback secret.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Comma-separated list via env supported by Pydantic (e.g. 'https://app.example.com,https://admin.example.com')
    cors_allow_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins. Do not use '*' when allow_credentials is enabled.",
    )

    # Convenience single-origin env var used by some deployments; if set, it will be merged into cors_allow_origins.
    cors_frontend_origin: Optional[str] = Field(
        default=None,
        description="Optional single frontend origin to add to CORS allowlist.",
        validation_alias="CORS_FRONTEND_ORIGIN",
    )

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
        # Merge convenience origin into allowlist (if provided).
        if self.cors_frontend_origin:
            origin = self.cors_frontend_origin.strip()
            if origin and origin not in self.cors_allow_origins:
                self.cors_allow_origins.append(origin)

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
