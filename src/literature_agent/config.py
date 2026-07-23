"""Application configuration helpers."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the application."""

    app_env: str = "development"


def load_config() -> AppConfig:
    """Load application settings from environment variables."""

    return AppConfig(app_env=os.getenv("APP_ENV", "development"))
