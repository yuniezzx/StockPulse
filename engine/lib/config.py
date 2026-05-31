from datetime import date
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
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
        default="", description="56-char token; empty in dev when not pulling data"
    )


settings = Settings()  # type: ignore[call-arg]
