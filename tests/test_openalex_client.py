from typing import Any

import pytest
import requests

from literature_agent.config import AppConfig
from literature_agent.openalex_client import OpenAlexClient
from literature_agent.works import SearchParams


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload

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


def test_fetch_works_uses_openalex_parameters_and_headers() -> None:
    session = FakeSession([FakeResponse(200, {"results": []})])
    config = AppConfig(openalex_user_agent="LiteratureAgent tests")
    client = OpenAlexClient(config=config, session=session, retry_delay_seconds=0)

    result = client.fetch_works(
        SearchParams(
            query="genome",
            from_date="2024-01-01",
            to_date="2024-12-31",
            max_results=5,
        )
    )

    assert result == {"results": []}
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "https://api.openalex.org/works"
    assert call["timeout"] == 30
    assert call["headers"]["User-Agent"] == "LiteratureAgent tests"
    assert call["params"]["search"] == "genome"
    assert call["params"]["per-page"] == 5
    assert call["params"]["filter"] == (
        "from_publication_date:2024-01-01,to_publication_date:2024-12-31"
    )


def test_fetch_works_retries_429_and_5xx_before_success() -> None:
    session = FakeSession(
        [
            FakeResponse(429, {}),
            FakeResponse(503, {}),
            FakeResponse(200, {"results": [{"id": "W1"}]}),
        ]
    )
    client = OpenAlexClient(session=session, retry_delay_seconds=0)

    result = client.fetch_works(
        SearchParams(
            query="rna",
            from_date="2024-01-01",
            to_date="2024-12-31",
            max_results=1,
        )
    )

    assert result == {"results": [{"id": "W1"}]}
    assert len(session.calls) == 3


def test_fetch_works_raises_after_retry_limit() -> None:
    session = FakeSession(
        [
            FakeResponse(500, {}),
            FakeResponse(500, {}),
            FakeResponse(500, {}),
            FakeResponse(500, {}),
        ]
    )
    client = OpenAlexClient(session=session, retry_delay_seconds=0)

    with pytest.raises(requests.HTTPError):
        client.fetch_works(
            SearchParams(
                query="rice",
                from_date="2024-01-01",
                to_date="2024-12-31",
                max_results=1,
            )
        )

    assert len(session.calls) == 4
