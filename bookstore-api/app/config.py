from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "change-me-use-openssl-rand-hex-32"
    super_admin_key: str = "super-secret-admin-key"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://bookstore:bookstore@localhost:5432/bookstore"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=50)

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate Limits (requests per minute) ─────────────────────────────────────
    rate_limit_free: int = Field(default=100, ge=1)
    rate_limit_pro: int = Field(default=1000, ge=1)
    rate_limit_enterprise: int = Field(default=10000, ge=1)

    # ── Tenant Cache ──────────────────────────────────────────────────────────
    tenant_cache_ttl_seconds: int = Field(default=300, ge=10)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def get_rate_limit_for_plan(self, plan: str) -> int:
        mapping = {
            "free": self.rate_limit_free,
            "pro": self.rate_limit_pro,
            "enterprise": self.rate_limit_enterprise,
        }
        return mapping.get(plan, self.rate_limit_free)


@lru_cache
def get_settings() -> Settings:
    return Settings()
