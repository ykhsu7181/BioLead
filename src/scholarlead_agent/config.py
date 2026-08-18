"""Application configuration helpers."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the application."""

    app_env: str = "development"
    openalex_base_url: str = "https://api.openalex.org"
    openalex_user_agent: str = "ScholarLeadAgent/0.1 (set OPENALEX_USER_AGENT for contact)"
    pubmed_esearch_url: str = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    )
    pubmed_efetch_url: str = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    )
    pubmed_user_agent: str = "ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)"
    ncbi_tool: str = "ScholarLeadAgent"
    ncbi_email: str | None = None
    ncbi_api_key: str | None = None
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
            "ScholarLeadAgent/0.1 (set OPENALEX_USER_AGENT for contact)",
        ),
        pubmed_esearch_url=os.getenv(
            "PUBMED_ESEARCH_URL",
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        ),
        pubmed_efetch_url=os.getenv(
            "PUBMED_EFETCH_URL",
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        ),
        pubmed_user_agent=os.getenv(
            "PUBMED_USER_AGENT",
            "ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)",
        ),
        ncbi_tool=os.getenv("NCBI_TOOL", "ScholarLeadAgent"),
        ncbi_email=os.getenv("NCBI_EMAIL") or None,
        ncbi_api_key=os.getenv("NCBI_API_KEY") or None,
    )

