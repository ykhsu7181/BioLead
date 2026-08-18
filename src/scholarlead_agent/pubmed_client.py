"""HTTP client for PubMed E-utilities."""

from __future__ import annotations

import time
from typing import Any, Sequence

import requests

from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.pubmed_models import PubMedSearchParams


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class PubMedClient:
    """Small client dedicated to PubMed ESearch and EFetch requests."""

    def __init__(
        self,
        config: AppConfig | None = None,
        session: requests.Session | None = None,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.config = config or load_config()
        self.session = session or requests.Session()
        self.retry_delay_seconds = retry_delay_seconds

    def esearch(self, params: PubMedSearchParams) -> dict[str, Any]:
        """Run PubMed ESearch and return the raw JSON response."""

        request_params: dict[str, Any] = {
            "db": "pubmed",
            "term": build_pubmed_search_term(params),
            "retmode": "json",
            "retmax": params.max_results,
            "sort": "pub date",
            "tool": self.config.ncbi_tool,
        }
        self._add_optional_ncbi_params(request_params)

        response = self._get(self.config.pubmed_esearch_url, params=request_params)
        return response.json()

    def efetch(self, pmids: Sequence[str]) -> str:
        """Run PubMed EFetch for PMIDs and return the raw XML text."""

        normalized_pmids = [pmid.strip() for pmid in pmids if pmid.strip()]
        if not normalized_pmids:
            raise ValueError("pmids cannot be empty")

        request_params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(normalized_pmids),
            "retmode": "xml",
            "rettype": "abstract",
            "tool": self.config.ncbi_tool,
        }
        self._add_optional_ncbi_params(request_params)

        response = self._get(self.config.pubmed_efetch_url, params=request_params)
        return response.text

    def _get(self, url: str, *, params: dict[str, Any]) -> requests.Response:
        headers = {"User-Agent": self.config.pubmed_user_agent}

        for attempt in range(self.config.retry_count + 1):
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.request_timeout_seconds,
            )

            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            if attempt == self.config.retry_count:
                response.raise_for_status()

            time.sleep(self.retry_delay_seconds)

        raise RuntimeError("PubMed request failed after retries")

    def _add_optional_ncbi_params(self, request_params: dict[str, Any]) -> None:
        if self.config.ncbi_email:
            request_params["email"] = self.config.ncbi_email
        if self.config.ncbi_api_key:
            request_params["api_key"] = self.config.ncbi_api_key


def build_pubmed_search_term(params: PubMedSearchParams) -> str:
    """Build a PubMed query term with publication date bounds."""

    return (
        f"({params.query}) AND "
        f'("{params.from_date}"[Date - Publication] : '
        f'"{params.to_date}"[Date - Publication])'
    )
