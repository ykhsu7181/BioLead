"""HTTP client for the OpenAlex Works API."""

from __future__ import annotations

import time
from typing import Any

import requests

from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.works import SearchParams


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenAlexClient:
    """Small client dedicated to OpenAlex Works API collection."""

    def __init__(
        self,
        config: AppConfig | None = None,
        session: requests.Session | None = None,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.config = config or load_config()
        self.session = session or requests.Session()
        self.retry_delay_seconds = retry_delay_seconds

    def fetch_works(self, params: SearchParams) -> dict[str, Any]:
        """Fetch works from OpenAlex and return the raw JSON response."""

        url = f"{self.config.openalex_base_url.rstrip('/')}/works"
        request_params = {
            "search": params.query,
            "filter": (
                f"from_publication_date:{params.from_date},"
                f"to_publication_date:{params.to_date}"
            ),
            "per-page": params.max_results,
            "page": 1,
            "select": (
                "id,doi,title,display_name,abstract_inverted_index,"
                "publication_date,authorships"
            ),
        }
        headers = {"User-Agent": self.config.openalex_user_agent}

        for attempt in range(self.config.retry_count + 1):
            response = self.session.get(
                url,
                params=request_params,
                headers=headers,
                timeout=self.config.request_timeout_seconds,
            )

            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response.json()

            if attempt == self.config.retry_count:
                response.raise_for_status()

            time.sleep(self.retry_delay_seconds)

        raise RuntimeError("OpenAlex request failed after retries")

