"""Configuracao da aplicacao. Segredos vem SOMENTE de variaveis de ambiente."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_PLACEHOLDER = "change-me"  # noqa: S105 - marcador, nunca um segredo real


class Settings(BaseSettings):
    """Todas as opcoes de runtime. Nenhum segredo tem default utilizavel em producao."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    TESTING: bool = Field(default=False)

    SECRET_KEY: str = Field(default=INSECURE_PLACEHOLDER)
    JWT_SECRET_KEY: str = Field(default=INSECURE_PLACEHOLDER)

    DATABASE_URL: str = Field(default="postgresql+psycopg://app:app@postgres:5432/mesas")
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="")
    CELERY_RESULT_BACKEND: str = Field(default="")

    ACCESS_TOKEN_TTL_SECONDS: int = Field(default=900)
    REFRESH_TOKEN_TTL_SECONDS: int = Field(default=60 * 60 * 24 * 14)
    COOKIE_SECURE: bool = Field(default=True)
    COOKIE_SAMESITE: str = Field(default="Lax")
    COOKIE_DOMAIN: str | None = Field(default=None)

    CORS_ORIGINS: str = Field(default="http://localhost:3000")
    RATELIMIT_DEFAULT: str = Field(default="200 per minute")
    RATELIMIT_AUTH: str = Field(default="10 per minute")
    RATELIMIT_QUEUE_JOIN: str = Field(default="5 per minute")
    RATELIMIT_ENABLED: bool = Field(default=True)

    SENTRY_DSN: str | None = Field(default=None)
    LOG_LEVEL: str = Field(default="INFO")

    DEFAULT_WAIT_MINUTES: int = Field(default=15)
    TURNOVER_SAMPLE_HOURS: int = Field(default=24)
    TURNOVER_SAMPLE_SIZE: int = Field(default=50)

    NOTIFICATION_PROVIDER: str = Field(default="mock")

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def _validate_samesite(cls, value: str) -> str:
        allowed = {"Lax", "Strict", "None"}
        if value not in allowed:
            raise ValueError(f"COOKIE_SAMESITE deve ser um de {sorted(allowed)}")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() in {"production", "prod"}

    def validate_runtime(self) -> None:
        """Falha rapido se producao subir com segredos placeholder."""
        if not self.is_production:
            return
        weak = [
            name
            for name in ("SECRET_KEY", "JWT_SECRET_KEY")
            if getattr(self, name) in (INSECURE_PLACEHOLDER, "", None)
        ]
        if weak:
            raise RuntimeError(
                "Configuracao insegura em producao: defina " + ", ".join(weak) + " via ambiente."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def build_settings(overrides: dict[str, object] | None = None) -> Settings:
    """Cria settings a partir do ambiente com overrides explicitos (usado em testes)."""
    data = {**os.environ, **(overrides or {})}
    known = {key: value for key, value in data.items() if key in Settings.model_fields}
    return Settings(**known)
