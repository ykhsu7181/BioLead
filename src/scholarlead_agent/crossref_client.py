"""HTTP client for the Crossref Works API."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests

from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.crossref_models import CrossrefSearchParams
from scholarlead_agent.pubmed_client import RETRYABLE_STATUS_CODES


class CrossrefClient:
    """Small client dedicated to Crossref Works API collection."""

    def __init__(
        self,
        config: AppConfig | None = None,
        session: requests.Session | None = None,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.config = config or load_config()
        self.session = session or requests.Session()
        self.retry_delay_seconds = retry_delay_seconds

    def search_works(self, params: CrossrefSearchParams) -> dict[str, Any]:
        """Fetch raw Crossref Works metadata by DOI or title."""

        response = self._get(
            _build_crossref_works_url(self.config.crossref_base_url, params),
            params=_build_crossref_request_params(params, self.config.crossref_mailto),
        )
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Crossref response must be a JSON object")
        return data

    def _get(self, url: str, *, params: dict[str, Any]) -> requests.Response:
        headers = {"User-Agent": self.config.crossref_user_agent}

        for attempt in range(self.config.retry_count + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.config.request_timeout_seconds,
                )
            except requests.RequestException:
                if attempt == self.config.retry_count:
                    raise
                time.sleep(self.retry_delay_seconds)
                continue

            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            if attempt == self.config.retry_count:
                response.raise_for_status()

            time.sleep(self.retry_delay_seconds)

        raise RuntimeError("Crossref request failed after retries")


def _build_crossref_works_url(base_url: str, params: CrossrefSearchParams) -> str:
    base = base_url.rstrip("/")
    if params.doi:
        return f"{base}/works/{quote(params.doi, safe='')}"
    return f"{base}/works"


def _build_crossref_request_params(
    params: CrossrefSearchParams,
    mailto: str | None,
) -> dict[str, Any]:
    request_params: dict[str, Any] = {}
    if params.doi is None:
        request_params["query.title"] = params.title
        request_params["rows"] = params.max_results
    if mailto:
        request_params["mailto"] = mailto
    return request_params
