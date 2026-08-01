"""Application configuration.

Settings are read from environment variables (optionally a `.env` file) so the
storage location can be swapped in tests without touching application code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="EXPENSE_", extra="ignore")

    app_name: str = "Expense Tracker API"
    version: str = "1.0.0"

    # Path to the JSON file used as the datastore. Override with EXPENSE_DATA_FILE.
    data_file: Path = BASE_DIR / "data" / "expenses.json"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — one config object per process."""
    return Settings()
