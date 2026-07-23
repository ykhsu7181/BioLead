"""Application configuration helpers."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the application."""

    app_env: str = "development"
    openalex_base_url: str = "https://api.openalex.org"
    openalex_user_agent: str = "LiteratureAgent/0.1 (set OPENALEX_USER_AGENT for contact)"
    request_timeout_seconds: int = 30
    retry_count: int = 3
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")


def load_config() -> AppConfig:
    """Load application settings from environment variables."""

    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        openalex_base_url=os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org"),
        openalex_user_agent=os.getenv(
            "OPENALEX_USER_AGENT",
            "LiteratureAgent/0.1 (set OPENALEX_USER_AGENT for contact)",
        ),
    )
