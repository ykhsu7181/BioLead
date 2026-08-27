import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scholarlead_agent import pubmed_main
from scholarlead_agent.pubmed_models import PubMedSearchParams, validate_pubmed_search_inputs
from scholarlead_agent.pubmed_storage import PubMedProcessedOutputPaths
from scholarlead_agent.services import pubmed_service
from scholarlead_agent.services.pubmed_service import run_pubmed_search
from scholarlead_agent.ui import streamlit_app


class FakePubMedClient:
    def __init__(
        self,
        *,
        esearch_response: dict[str, Any] | None = None,
        esearch_error: Exception | None = None,
        efetch_xml: str = "<PubmedArticleSet />",
        efetch_error: Exception | None = None,
    ) -> None:
        self.esearch_response = esearch_response or {
            "esearchresult": {"idlist": ["12345678", "87654321"]}
        }
        self.esearch_error = esearch_error
        self.efetch_xml = efetch_xml
        self.efetch_error = efetch_error
        self.esearch_calls = 0
        self.efetch_calls: list[list[str]] = []

    def esearch(self, params: PubMedSearchParams) -> dict[str, Any]:
        self.esearch_calls += 1
        if self.esearch_error is not None:
            raise self.esearch_error
        return self.esearch_response

    def efetch(self, pmids: list[str]) -> str:
        self.efetch_calls.append(pmids)
        if self.efetch_error is not None:
            raise self.efetch_error
        return self.efetch_xml


def make_params(tmp_path: Path) -> PubMedSearchParams:
    return PubMedSearchParams(
        query="single-cell RNA sequencing cancer",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=10,
        country="US",
        service_type="scRNA-seq",
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )


def test_run_pubmed_search_returns_stable_structured_result(tmp_path: Path) -> None:
    fixture_xml = Path("tests/fixtures/pubmed_efetch_response.xml").read_text(
        encoding="utf-8"
    )
    params = make_params(tmp_path)
    fake_client = FakePubMedClient(efetch_xml=fixture_xml)

    result = run_pubmed_search(
        params,
        client=fake_client,
        timestamp="20260820_120000",
        task_id="pubmed-stage20a",
        started_at="2026-08-20T12:00:00",
        finished_at="2026-08-20T12:00:01",
    )

    assert result.task_id == "pubmed-stage20a"
    assert result.status == "success"
    assert result.search_params == params
    assert result.started_at == "2026-08-20T12:00:00"
    assert result.finished_at == "2026-08-20T12:00:01"
    assert result.pmids == ["12345678", "87654321"]
    assert len(result.papers) == 2
    assert len(result.leads) == 2
    assert result.raw_files["esearch_json"].endswith("_esearch.json")
    assert result.processed_files["papers_csv"].endswith(".csv")
    assert result.raw_paths.esearch_json.exists()
    assert result.raw_paths.efetch_xml.exists()
    assert result.processed_paths.papers_json.exists()
    assert result.processed_paths.leads_csv.exists()
    assert result.run_report_path.exists()
    assert result.run_report["status"] == "success"
    assert result.errors == []
    assert fake_client.esearch_calls == 1
    assert fake_client.efetch_calls == [["12345678", "87654321"]]


def test_run_pubmed_search_records_esearch_failure_without_real_network(
    tmp_path: Path,
) -> None:
    params = make_params(tmp_path)
    fake_client = FakePubMedClient(esearch_error=RuntimeError("ESearch failed"))

    result = run_pubmed_search(
        params,
        client=fake_client,
        timestamp="20260820_120000",
        started_at="2026-08-20T12:00:00",
        finished_at="2026-08-20T12:00:01",
    )

    assert result.status == "failed"
    assert result.pmids == []
    assert result.papers == []
    assert result.leads == []
    assert result.errors == [
        {
            "stage": "esearch",
            "type": "RuntimeError",
            "message": "ESearch failed",
        }
    ]
    assert result.run_report["status"] == "failed"
    assert result.run_report_path.exists()
    assert fake_client.esearch_calls == 1
    assert fake_client.efetch_calls == []


def test_run_pubmed_search_keeps_esearch_raw_when_efetch_fails(
    tmp_path: Path,
) -> None:
    params = make_params(tmp_path)
    fake_client = FakePubMedClient(efetch_error=RuntimeError("EFetch failed"))

    result = run_pubmed_search(
        params,
        client=fake_client,
        timestamp="20260820_120000",
        started_at="2026-08-20T12:00:00",
        finished_at="2026-08-20T12:00:01",
    )

    assert result.status == "partial_failure"
    assert result.pmids == ["12345678", "87654321"]
    assert result.raw_paths.esearch_json.exists()
    assert result.raw_paths.request_meta_json.exists()
    assert not result.raw_paths.efetch_xml.exists()
    assert result.processed_files == {}
    assert result.errors[0]["stage"] == "efetch"

    saved_esearch = json.loads(result.raw_paths.esearch_json.read_text(encoding="utf-8"))
    assert saved_esearch == {"esearchresult": {"idlist": ["12345678", "87654321"]}}


def test_validate_rejects_invalid_params_before_service_client_is_needed() -> None:
    with pytest.raises(ValueError, match="from_date must be earlier"):
        validate_pubmed_search_inputs(
            query="genome",
            from_date="2024-12-31",
            to_date="2024-01-01",
            max_results=10,
        )


def test_pubmed_cli_calls_shared_service(monkeypatch, tmp_path: Path) -> None:
    calls: list[PubMedSearchParams] = []
    processed_paths = PubMedProcessedOutputPaths(
        papers_json=tmp_path / "papers.json",
        papers_csv=tmp_path / "papers.csv",
        leads_json=tmp_path / "leads.json",
        leads_csv=tmp_path / "leads.csv",
    )

    def fake_run_pubmed_search(
        params: PubMedSearchParams,
        *,
        client: object | None = None,
    ) -> object:
        calls.append(params)
        return SimpleNamespace(
            task_id="pubmed-cli-test",
            status="success",
            pmids=[],
            papers=[],
            leads=[],
            processed_paths=processed_paths,
            run_report_path=tmp_path / "run_report.json",
            run_report={
                "leads_with_verified_email_count": 0,
                "leads_needing_review_count": 0,
                "unknown_country_count": 0,
                "raw_files": {},
            },
        )

    monkeypatch.setattr(pubmed_main, "run_pubmed_search", fake_run_pubmed_search)
    monkeypatch.setattr(pubmed_main, "PubMedClient", lambda: object())

    exit_code = pubmed_main.main(
        [
            "--query",
            "genome",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-12-31",
            "--max-results",
            "5",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--processed-dir",
            str(tmp_path / "processed"),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0].query == "genome"
    assert calls[0].max_results == 5


def test_streamlit_ui_imports_same_shared_service_entrypoint() -> None:
    assert streamlit_app.run_pubmed_search is pubmed_service.run_pubmed_search
