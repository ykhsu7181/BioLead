from typing import Any

import pytest
import requests

from scholarlead_agent.config import AppConfig
from scholarlead_agent.nih_reporter_client import (
    NIHReporterClient,
    build_nih_reporter_project_payload,
)
from scholarlead_agent.nih_reporter_models import validate_nih_reporter_search_inputs


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload or {"results": []}
        self.json_error = json_error

    def json(self) -> dict[str, Any]:
        if self.json_error is not None:
            raise self.json_error
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(
        self,
        responses: list[FakeResponse] | None = None,
        error: requests.RequestException | None = None,
    ) -> None:
        self.responses = responses or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


def make_config(**overrides: Any) -> AppConfig:
    values = {
        "nih_reporter_projects_search_url": "https://api.reporter.test/v2/projects/search",
        "nih_reporter_user_agent": "ScholarLeadAgent/0.1 test",
        "request_timeout_seconds": 30,
        "retry_count": 1,
    }
    values.update(overrides)
    return AppConfig(**values)


def test_build_nih_reporter_project_payload_uses_expected_criteria() -> None:
    params = validate_nih_reporter_search_inputs(
        pi_name="Lei S Qi",
        institution="Stanford University",
        keyword="CRISPR imaging",
        from_year=2024,
        to_year=2026,
        max_results=5,
    )

    payload = build_nih_reporter_project_payload(params)

    assert payload["criteria"]["fiscal_years"] == [2024, 2025, 2026]
    assert payload["criteria"]["pi_names"] == [{"any_name": "Lei S Qi"}]
    assert payload["criteria"]["org_names"] == ["Stanford University"]
    assert payload["criteria"]["advanced_text_search"]["search_text"] == "CRISPR imaging"
    assert payload["limit"] == 5


def test_nih_reporter_client_posts_with_user_agent_and_timeout() -> None:
    session = FakeSession([FakeResponse(200, {"results": [{"appl_id": 1}]})])
    client = NIHReporterClient(
        config=make_config(),
        session=session,
        retry_delay_seconds=0,
    )
    params = validate_nih_reporter_search_inputs(
        keyword="cancer",
        from_year=2025,
        to_year=2025,
        max_results=2,
    )

    result = client.search_projects(params)

    assert result["results"][0]["appl_id"] == 1
    assert session.calls[0]["url"] == "https://api.reporter.test/v2/projects/search"
    assert session.calls[0]["headers"]["User-Agent"] == "ScholarLeadAgent/0.1 test"
    assert session.calls[0]["headers"]["Content-Type"] == "application/json"
    assert session.calls[0]["timeout"] == 30
    assert session.calls[0]["json"]["criteria"]["advanced_text_search"]["search_text"] == "cancer"


def test_nih_reporter_client_retries_retryable_status() -> None:
    session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(200, {"results": [{"project_num": "R01CA123"}]}),
        ]
    )
    client = NIHReporterClient(
        config=make_config(retry_count=1),
        session=session,
        retry_delay_seconds=0,
    )

    result = client.search_projects(
        validate_nih_reporter_search_inputs(
            pi_name="Jane Doe",
            from_year=2024,
            to_year=2024,
            max_results=1,
        )
    )

    assert result["results"][0]["project_num"] == "R01CA123"
    assert len(session.calls) == 2


def test_nih_reporter_client_raises_for_non_retryable_http_error() -> None:
    session = FakeSession([FakeResponse(404)])
    client = NIHReporterClient(config=make_config(), session=session)

    with pytest.raises(requests.HTTPError, match="HTTP 404"):
        client.search_projects(
            validate_nih_reporter_search_inputs(
                keyword="missing",
                from_year=2024,
                to_year=2024,
                max_results=1,
            )
        )


def test_nih_reporter_client_retries_timeout_then_raises() -> None:
    session = FakeSession(error=requests.Timeout("timeout"))
    client = NIHReporterClient(
        config=make_config(retry_count=1),
        session=session,
        retry_delay_seconds=0,
    )

    with pytest.raises(requests.Timeout):
        client.search_projects(
            validate_nih_reporter_search_inputs(
                keyword="cancer",
                from_year=2024,
                to_year=2024,
                max_results=1,
            )
        )
    assert len(session.calls) == 2


def test_nih_reporter_client_raises_for_malformed_json() -> None:
    session = FakeSession([FakeResponse(200, json_error=ValueError("bad json"))])
    client = NIHReporterClient(config=make_config(), session=session)

    with pytest.raises(ValueError, match="bad json"):
        client.search_projects(
            validate_nih_reporter_search_inputs(
                keyword="cancer",
                from_year=2024,
                to_year=2024,
                max_results=1,
            )
        )
