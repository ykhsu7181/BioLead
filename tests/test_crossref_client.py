from typing import Any

import pytest
import requests

from scholarlead_agent.config import AppConfig
from scholarlead_agent.crossref_client import CrossrefClient
from scholarlead_agent.crossref_models import validate_crossref_search_inputs


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload or {"message": {"items": []}}
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

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


def make_config(**overrides: Any) -> AppConfig:
    values = {
        "crossref_base_url": "https://api.crossref.test",
        "crossref_user_agent": "ScholarLeadAgent/0.1 test",
        "crossref_mailto": "contact@example.test",
        "request_timeout_seconds": 30,
        "retry_count": 1,
    }
    values.update(overrides)
    return AppConfig(**values)


def test_crossref_client_uses_doi_endpoint_and_mailto() -> None:
    session = FakeSession([FakeResponse(200, {"message": {"DOI": "10.1038/abc"}})])
    client = CrossrefClient(
        config=make_config(),
        session=session,
        retry_delay_seconds=0,
    )
    params = validate_crossref_search_inputs(
        doi="10.1038/ABC/123",
        title="ignored",
        max_results=5,
    )

    result = client.search_works(params)

    assert result["message"]["DOI"] == "10.1038/abc"
    assert session.calls[0]["url"] == "https://api.crossref.test/works/10.1038%2Fabc%2F123"
    assert session.calls[0]["params"] == {"mailto": "contact@example.test"}
    assert session.calls[0]["headers"]["User-Agent"] == "ScholarLeadAgent/0.1 test"
    assert session.calls[0]["timeout"] == 30


def test_crossref_client_uses_title_query_when_doi_missing() -> None:
    session = FakeSession([FakeResponse(200)])
    client = CrossrefClient(config=make_config(crossref_mailto=None), session=session)
    params = validate_crossref_search_inputs(title="single cell cancer", max_results=7)

    client.search_works(params)

    assert session.calls[0]["url"] == "https://api.crossref.test/works"
    assert session.calls[0]["params"] == {
        "query.title": "single cell cancer",
        "rows": 7,
    }


def test_crossref_client_retries_retryable_status() -> None:
    session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(200, {"message": {"items": [{"DOI": "10.1/x"}]}}),
        ]
    )
    client = CrossrefClient(
        config=make_config(retry_count=1),
        session=session,
        retry_delay_seconds=0,
    )

    result = client.search_works(
        validate_crossref_search_inputs(title="crispr", max_results=2)
    )

    assert result["message"]["items"][0]["DOI"] == "10.1/x"
    assert len(session.calls) == 2


def test_crossref_client_raises_for_non_retryable_http_error() -> None:
    session = FakeSession([FakeResponse(404)])
    client = CrossrefClient(config=make_config(), session=session)

    with pytest.raises(requests.HTTPError, match="HTTP 404"):
        client.search_works(validate_crossref_search_inputs(title="missing", max_results=1))


def test_crossref_client_retries_timeout_then_raises() -> None:
    session = FakeSession(error=requests.Timeout("timeout"))
    client = CrossrefClient(
        config=make_config(retry_count=1),
        session=session,
        retry_delay_seconds=0,
    )

    with pytest.raises(requests.Timeout):
        client.search_works(validate_crossref_search_inputs(title="crispr", max_results=2))
    assert len(session.calls) == 2


def test_crossref_client_raises_for_malformed_json() -> None:
    session = FakeSession([FakeResponse(200, json_error=ValueError("bad json"))])
    client = CrossrefClient(config=make_config(), session=session)

    with pytest.raises(ValueError, match="bad json"):
        client.search_works(validate_crossref_search_inputs(title="crispr", max_results=2))
