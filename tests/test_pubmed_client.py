from typing import Any

import pytest
import requests

from scholarlead_agent.config import AppConfig
from scholarlead_agent.pubmed_client import PubMedClient, build_pubmed_search_term
from scholarlead_agent.pubmed_models import PubMedSearchParams


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.payload = payload or {}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def make_params() -> PubMedSearchParams:
    return PubMedSearchParams(
        query="single cell RNA sequencing",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=25,
        country="US",
        service_type="scRNA-seq",
    )


def test_build_pubmed_search_term_includes_query_and_publication_dates() -> None:
    term = build_pubmed_search_term(make_params())

    assert "(single cell RNA sequencing)" in term
    assert '"2024-01-01"[Date - Publication]' in term
    assert '"2024-12-31"[Date - Publication]' in term


def test_esearch_uses_pubmed_parameters_headers_and_optional_ncbi_fields() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"esearchresult": {"idlist": ["123", "456"]}},
            )
        ]
    )
    config = AppConfig(
        pubmed_esearch_url="https://example.test/esearch.fcgi",
        pubmed_user_agent="ScholarLeadAgent tests",
        ncbi_tool="ScholarLeadAgentTest",
        ncbi_email="tester@example.com",
        ncbi_api_key="test-key",
    )
    client = PubMedClient(config=config, session=session, retry_delay_seconds=0)

    result = client.esearch(make_params())

    assert result == {"esearchresult": {"idlist": ["123", "456"]}}
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "https://example.test/esearch.fcgi"
    assert call["timeout"] == 30
    assert call["headers"]["User-Agent"] == "ScholarLeadAgent tests"
    assert call["params"]["db"] == "pubmed"
    assert call["params"]["retmode"] == "json"
    assert call["params"]["retmax"] == 25
    assert call["params"]["sort"] == "pub date"
    assert call["params"]["tool"] == "ScholarLeadAgentTest"
    assert call["params"]["email"] == "tester@example.com"
    assert call["params"]["api_key"] == "test-key"
    assert "single cell RNA sequencing" in call["params"]["term"]


def test_esearch_omits_optional_ncbi_fields_when_not_configured() -> None:
    session = FakeSession([FakeResponse(200, {"esearchresult": {"idlist": []}})])
    client = PubMedClient(
        config=AppConfig(ncbi_email=None, ncbi_api_key=None),
        session=session,
        retry_delay_seconds=0,
    )

    client.esearch(make_params())

    request_params = session.calls[0]["params"]
    assert "email" not in request_params
    assert "api_key" not in request_params


def test_efetch_uses_pubmed_parameters_and_returns_xml_text() -> None:
    session = FakeSession([FakeResponse(200, text="<PubmedArticleSet />")])
    config = AppConfig(
        pubmed_efetch_url="https://example.test/efetch.fcgi",
        pubmed_user_agent="ScholarLeadAgent tests",
        ncbi_tool="ScholarLeadAgentTest",
        ncbi_email="tester@example.com",
    )
    client = PubMedClient(config=config, session=session, retry_delay_seconds=0)

    result = client.efetch(["123", " 456 "])

    assert result == "<PubmedArticleSet />"
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "https://example.test/efetch.fcgi"
    assert call["timeout"] == 30
    assert call["headers"]["User-Agent"] == "ScholarLeadAgent tests"
    assert call["params"]["db"] == "pubmed"
    assert call["params"]["id"] == "123,456"
    assert call["params"]["retmode"] == "xml"
    assert call["params"]["rettype"] == "abstract"
    assert call["params"]["tool"] == "ScholarLeadAgentTest"
    assert call["params"]["email"] == "tester@example.com"


def test_efetch_rejects_empty_pmids_before_http_call() -> None:
    session = FakeSession([])
    client = PubMedClient(session=session, retry_delay_seconds=0)

    with pytest.raises(ValueError, match="pmids cannot be empty"):
        client.efetch([" ", ""])

    assert session.calls == []


def test_pubmed_client_retries_429_and_5xx_before_success() -> None:
    session = FakeSession(
        [
            FakeResponse(429),
            FakeResponse(503),
            FakeResponse(200, {"esearchresult": {"idlist": ["789"]}}),
        ]
    )
    client = PubMedClient(session=session, retry_delay_seconds=0)

    result = client.esearch(make_params())

    assert result == {"esearchresult": {"idlist": ["789"]}}
    assert len(session.calls) == 3


def test_pubmed_client_raises_after_retry_limit() -> None:
    session = FakeSession(
        [
            FakeResponse(500),
            FakeResponse(500),
            FakeResponse(500),
            FakeResponse(500),
        ]
    )
    client = PubMedClient(session=session, retry_delay_seconds=0)

    with pytest.raises(requests.HTTPError):
        client.esearch(make_params())

    assert len(session.calls) == 4


def test_pubmed_client_does_not_retry_non_retryable_status() -> None:
    session = FakeSession([FakeResponse(400)])
    client = PubMedClient(session=session, retry_delay_seconds=0)

    with pytest.raises(requests.HTTPError):
        client.esearch(make_params())

    assert len(session.calls) == 1
