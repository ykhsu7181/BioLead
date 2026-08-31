"""Application configuration helpers."""

from dataclasses import dataclass
import os
from pathlib import Path

_DOTENV_LOADED = False


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the application."""

    app_env: str = "development"
    openalex_base_url: str = "https://api.openalex.org"
    openalex_user_agent: str = "ScholarLeadAgent/0.1 (set OPENALEX_USER_AGENT for contact)"
    crossref_base_url: str = "https://api.crossref.org"
    crossref_user_agent: str = "ScholarLeadAgent/0.1 (set CROSSREF_MAILTO for contact)"
    crossref_mailto: str | None = None
    nih_reporter_base_url: str = "https://api.reporter.nih.gov"
    nih_reporter_projects_search_url: str = (
        "https://api.reporter.nih.gov/v2/projects/search"
    )
    nih_reporter_user_agent: str = (
        "ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)"
    )
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
    openai_provider: str = "openai_compatible"
    openai_account_alias: str = "default"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    openai_fallback_model: str | None = None
    agent_default_model: str | None = None
    agent_max_results_limit: int = 50
    email_draft_default_model: str | None = None
    ai_usage_dir: Path = Path("data/processed/ai_usage")
    email_audit_dir: Path = Path("data/processed/email_audit")
    token_warning_threshold: int | None = None
    cost_warning_threshold: float | None = None
    ai_pricing_config_version: str = "unconfigured"
    request_timeout_seconds: int = 30
    retry_count: int = 3
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    database_path: Path = Path("data/processed/scholarlead_agent.sqlite")
    email_provider: str = "disabled"
    email_send_enabled: bool = False
    email_sender: str | None = None
    email_test_recipient: str | None = None
    email_allowed_recipients: tuple[str, ...] = ()
    email_daily_limit: int = 0
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_ssl: bool = True
    smtp_timeout_seconds: int = 30

    def __post_init__(self) -> None:
        if (
            isinstance(self.agent_max_results_limit, bool)
            or not isinstance(self.agent_max_results_limit, int)
            or self.agent_max_results_limit <= 0
        ):
            raise ValueError("agent_max_results_limit must be a positive integer")


def load_config() -> AppConfig:
    """Load application settings from environment variables and local .env."""

    _load_dotenv_once()
    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        openalex_base_url=os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org"),
        openalex_user_agent=os.getenv(
            "OPENALEX_USER_AGENT",
            "ScholarLeadAgent/0.1 (set OPENALEX_USER_AGENT for contact)",
        ),
        crossref_base_url=os.getenv("CROSSREF_BASE_URL", "https://api.crossref.org"),
        crossref_user_agent=os.getenv(
            "CROSSREF_USER_AGENT",
            "ScholarLeadAgent/0.1 (set CROSSREF_MAILTO for contact)",
        ),
        crossref_mailto=os.getenv("CROSSREF_MAILTO") or None,
        nih_reporter_base_url=os.getenv(
            "NIH_REPORTER_BASE_URL",
            "https://api.reporter.nih.gov",
        ),
        nih_reporter_projects_search_url=os.getenv(
            "NIH_REPORTER_PROJECTS_SEARCH_URL",
            "https://api.reporter.nih.gov/v2/projects/search",
        ),
        nih_reporter_user_agent=os.getenv(
            "NIH_REPORTER_USER_AGENT",
            "ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)",
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
        openai_provider=os.getenv("OPENAI_PROVIDER", "openai_compatible"),
        openai_account_alias=os.getenv("OPENAI_ACCOUNT_ALIAS", "default"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        openai_model=os.getenv("OPENAI_MODEL") or None,
        openai_fallback_model=os.getenv("OPENAI_FALLBACK_MODEL") or None,
        agent_default_model=os.getenv("AGENT_DEFAULT_MODEL") or None,
        agent_max_results_limit=_positive_int_env(
            "AGENT_MAX_RESULTS_LIMIT",
            default=50,
        ),
        email_draft_default_model=os.getenv("EMAIL_DRAFT_DEFAULT_MODEL") or None,
        ai_usage_dir=Path(os.getenv("AI_USAGE_DIR", "data/processed/ai_usage")),
        email_audit_dir=Path(
            os.getenv("EMAIL_AUDIT_DIR", "data/processed/email_audit")
        ),
        token_warning_threshold=_optional_int_env("TOKEN_WARNING_THRESHOLD"),
        cost_warning_threshold=_optional_float_env("COST_WARNING_THRESHOLD"),
        ai_pricing_config_version=os.getenv(
            "AI_PRICING_CONFIG_VERSION",
            "unconfigured",
        ),
        database_path=Path(
            os.getenv("DATABASE_PATH", "data/processed/scholarlead_agent.sqlite")
        ),
        email_provider=os.getenv("EMAIL_PROVIDER", "disabled"),
        email_send_enabled=_optional_bool_env("EMAIL_SEND_ENABLED", default=False),
        email_sender=os.getenv("EMAIL_SENDER") or None,
        email_test_recipient=os.getenv("EMAIL_TEST_RECIPIENT") or None,
        email_allowed_recipients=_tuple_env("EMAIL_ALLOWED_RECIPIENTS"),
        email_daily_limit=_optional_int_env("EMAIL_DAILY_LIMIT") or 0,
        smtp_host=os.getenv("SMTP_HOST") or None,
        smtp_port=_optional_int_env("SMTP_PORT") or 465,
        smtp_username=os.getenv("SMTP_USERNAME") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        smtp_use_ssl=_optional_bool_env("SMTP_USE_SSL", default=True),
        smtp_timeout_seconds=_optional_int_env("SMTP_TIMEOUT_SECONDS") or 30,
    )


def _load_dotenv_once() -> None:
    """Load project-local .env values without overriding existing environment."""

    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _optional_bool_env(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _tuple_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return int(value)


def _positive_int_env(name: str, *, default: int) -> int:
    """Read one required positive integer setting with a default."""

    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _optional_float_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return float(value)

