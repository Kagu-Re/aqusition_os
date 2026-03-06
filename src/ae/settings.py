from __future__ import annotations

from typing import List, Optional

try:
    # pydantic-settings (recommended with pydantic v2)
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover
    # fallback: BaseSettings may exist depending on pydantic install
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore

from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Central configuration contract.

    Keep this small and explicit. Prefer edge-level security controls, but expose
    the minimal knobs needed for portable deployments.
    """

    model_config = SettingsConfigDict(
        env_prefix="AE_",
        case_sensitive=False,
        extra="ignore",
    )

    # Public API
    public_cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    lead_rl_per_min: float = 30.0
    lead_rl_burst: float = 60.0

    # Console
    console_secret: str = ""

    # DB (sqlite today; url supported)
    db_url: str = ""

    # Multi-tenant (optional; default off)
    multi_tenant_enabled: bool = False

    @field_validator("public_cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if v is None:
            return ["*"]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["*"]
            # comma-separated
            parts = [p.strip() for p in s.split(",")]
            return [p for p in parts if p]
        if isinstance(v, list):
            return v
        return ["*"]

    @field_validator("lead_rl_per_min", "lead_rl_burst", mode="before")
    @classmethod
    def _nonneg(cls, v):
        try:
            fv = float(v)
        except Exception:
            return 0.0
        return max(0.0, fv)

    @field_validator("multi_tenant_enabled", mode="before")
    @classmethod
    def _parse_bool(cls, v):
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "y")


def get_settings() -> Settings:
    return Settings()
