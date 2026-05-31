"""Application settings loaded from the repo-root .env file.

Loader strategy (D1-a):
    pulse-core is run standalone (cron / shell), no parent process injects env.
    We explicitly point pydantic-settings at the repo-root .env so that
    `cd pulse-core && uv run python -m pulse_core.xxx` works out of the box.
"""

from datetime import date
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# pulse-core/pulse_core/lib/config.py → parents: [lib, pulse_core, pulse-core, <repo root>]
REPO_ROOT = Path(__file__).resolve().parents[3]

# Earliest trade date we ingest history for. Tune per data scope (10y plan in docs).
HISTORY_START_DATE: date = date(2023, 1, 1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(min_length=1)
    TUSHARE_API_URL: str = Field(min_length=1)
    TUSHARE_TOKEN: str = Field(
        default="",
        description="56-char Tushare Pro token; empty in dev when not pulling data.",
    )
    CORE_LOG_LEVEL: str = Field(
        default="INFO",
        description="Loguru level: TRACE/DEBUG/INFO/WARNING/ERROR/CRITICAL.",
    )


settings = Settings()  # type: ignore[call-arg]
