"""Application configuration via Pydantic Settings.

All environment variables are validated at startup. Missing required
variables raise a clear error rather than failing at runtime.
"""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ───────────────────────────────────────────
    APP_NAME: str = "Aevix"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    APP_ENV: str = "development"

    # ─── Server ────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    BACKEND_CORS_ALLOW_CREDENTIALS: bool = True

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ─── Database ──────────────────────────────────────────────
    DATABASE_URL: MultiHostUrl = MultiHostUrl(
        "postgresql+asyncpg://aevix:aevix@localhost:5432/aevix"
    )

    # ─── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── Security ──────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    DEFAULT_ROLE: str = "user"

    # ─── Rate Limiting (Auth) ──────────────────────────────────
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ─── Cookies (Refresh Token) ───────────────────────────────
    COOKIE_DOMAIN: str = ""
    REFRESH_TOKEN_COOKIE_NAME: str = "aevix_refresh"
    REFRESH_TOKEN_COOKIE_PATH: str = "/api/v1/auth"
    REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES: int = 0  # 0 = disabled

    # ─── Email Verification ────────────────────────────────────
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # ─── SMTP (placeholder — configure for production) ────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Aevix"
    SMTP_FROM_EMAIL: str = "noreply@aevix.ai"

    # ─── File Storage ──────────────────────────────────────────
    STORAGE_MAX_SIZE_MB: int = 50
    STORAGE_UPLOAD_DIR: str = "./storage"
    STORAGE_S3_BUCKET: str = ""

    # ─── AI ────────────────────────────────────────────────────
    AI_DEFAULT_PROVIDER: str = "openai"
    AI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ─── Vector Store ──────────────────────────────────────────
    VECTOR_STORE_TYPE: str = "pgvector"

    # ─── Derived Properties ────────────────────────────────────
    @property
    def database_dsn(self) -> str:
        return str(self.DATABASE_URL)

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
