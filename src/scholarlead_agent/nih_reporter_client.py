"""HTTP client for the NIH RePORTER Project API."""

from __future__ import annotations

import time
from typing import Any

import requests

from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.nih_reporter_models import NIHReporterSearchParams
from scholarlead_agent.pubmed_client import RETRYABLE_STATUS_CODES


class NIHReporterClient:
    """Small client dedicated to NIH RePORTER project searches."""

    def __init__(
        self,
        config: AppConfig | None = None,
        session: requests.Session | None = None,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.config = config or load_config()
        self.session = session or requests.Session()
        self.retry_delay_seconds = retry_delay_seconds

    def search_projects(self, params: NIHReporterSearchParams) -> dict[str, Any]:
        """Fetch raw NIH RePORTER project records."""

        response = self._post(
            self.config.nih_reporter_projects_search_url,
            json_payload=build_nih_reporter_project_payload(params),
        )
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("NIH RePORTER response must be a JSON object")
        return data

    def _post(self, url: str, *, json_payload: dict[str, Any]) -> requests.Response:
        headers = {
            "User-Agent": self.config.nih_reporter_user_agent,
            "Content-Type": "application/json",
        }

        for attempt in range(self.config.retry_count + 1):
            try:
                response = self.session.post(
                    url,
                    json=json_payload,
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

        raise RuntimeError("NIH RePORTER request failed after retries")


def build_nih_reporter_project_payload(
    params: NIHReporterSearchParams,
) -> dict[str, Any]:
    """Build a minimal NIH RePORTER project search payload."""

    criteria: dict[str, Any] = {
        "fiscal_years": list(range(params.from_year, params.to_year + 1)),
    }
    if params.pi_name:
        criteria["pi_names"] = [{"any_name": params.pi_name}]
    if params.institution:
        criteria["org_names"] = [params.institution]
    if params.keyword:
        criteria["advanced_text_search"] = {
            "operator": "and",
            "search_field": "projecttitle,terms,abstracttext",
            "search_text": params.keyword,
        }

    return {
        "criteria": criteria,
        "include_fields": [
            "ApplId",
            "ProjectNum",
            "CoreProjectNum",
            "ProjectTitle",
            "FiscalYear",
            "Organization",
            "PrincipalInvestigators",
            "AwardAmount",
            "ProjectStartDate",
            "ProjectEndDate",
            "AgencyIcAdmin",
            "ProjectDetailUrl",
        ],
        "offset": 0,
        "limit": params.max_results,
        "sort_field": "fiscal_year",
        "sort_order": "desc",
    }
