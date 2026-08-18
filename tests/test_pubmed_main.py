import json
from pathlib import Path

import pytest

from scholarlead_agent.pubmed_main import main


class FakePubMedClient:
    def __init__(
        self,
        *,
        esearch_response: dict[str, object] | None = None,
        efetch_xml: str = "<PubmedArticleSet />",
        efetch_error: Exception | None = None,
    ) -> None:
        self.esearch_response = esearch_response or {
            "esearchresult": {"idlist": ["12345678", "87654321"]}
        }
        self.efetch_xml = efetch_xml
        self.efetch_error = efetch_error
        self.esearch_calls = 0
        self.efetch_calls: list[list[str]] = []

    def esearch(self, params):
        self.esearch_calls += 1
        return self.esearch_response

    def efetch(self, pmids: list[str]) -> str:
        self.efetch_calls.append(pmids)
        if self.efetch_error is not None:
            raise self.efetch_error
        return self.efetch_xml


def test_pubmed_main_runs_mock_end_to_end_without_real_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    fixture_xml = Path("tests/fixtures/pubmed_efetch_response.xml").read_text(
        encoding="utf-8"
    )
    fake_client = FakePubMedClient(efetch_xml=fixture_xml)
    monkeypatch.setattr(
        "scholarlead_agent.pubmed_main.PubMedClient",
        lambda: fake_client,
    )

    exit_code = main(
        [
            "--query",
            "single-cell RNA sequencing cancer",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-12-31",
            "--max-results",
            "25",
            "--country",
            "us",
            "--service-type",
            "scRNA-seq",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--processed-dir",
            str(tmp_path / "processed"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert fake_client.esearch_calls == 1
    assert fake_client.efetch_calls == [["12345678", "87654321"]]
    assert "ScholarLead Agent PubMed first-round run completed" in captured.out
    assert "Status: success" in captured.out
    assert "PMIDs collected: 2" in captured.out
    assert "Papers parsed: 2" in captured.out
    assert "Leads generated: 2" in captured.out
    assert "Scoring mode: PubMed single-source temporary scoring" in captured.out
    assert "LLM used: no" in captured.out
    assert "Agent enabled: no" in captured.out

    raw_files = list((tmp_path / "raw").glob("*"))
    processed_files = list((tmp_path / "processed").glob("*"))
    assert any(path.name.endswith("_esearch.json") for path in raw_files)
    assert any(path.name.endswith("_efetch.xml") for path in raw_files)
    assert any(path.name.endswith("_request_meta.json") for path in raw_files)
    assert any(path.name.startswith("pubmed_papers_") for path in processed_files)
    assert any(path.name.startswith("pubmed_leads_") for path in processed_files)
    assert any(path.name.startswith("pubmed_run_report_") for path in processed_files)

    report_path = next(
        path
        for path in processed_files
        if path.name.startswith("pubmed_run_report_")
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "success"
    assert report["pmid_count"] == 2
    assert report["paper_count"] == 2
    assert report["lead_count"] == 2
    assert report["scoring_mode"] == "pubmed_single_source_temporary"


def test_pubmed_main_records_partial_failure_without_deleting_raw(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    fake_client = FakePubMedClient(efetch_error=RuntimeError("EFetch failed"))
    monkeypatch.setattr(
        "scholarlead_agent.pubmed_main.PubMedClient",
        lambda: fake_client,
    )

    exit_code = main(
        [
            "--query",
            "genome assembly",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-12-31",
            "--max-results",
            "10",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--processed-dir",
            str(tmp_path / "processed"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Status: partial_failure" in captured.out
    assert any((tmp_path / "raw").glob("*_esearch.json"))
    assert any((tmp_path / "raw").glob("*_request_meta.json"))

    report_path = next((tmp_path / "processed").glob("pubmed_run_report_*.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "partial_failure"
    assert report["pmid_count"] == 2
    assert report["errors"][0]["stage"] == "efetch"
    assert report["errors"][0]["message"] == "EFetch failed"


def test_pubmed_main_rejects_invalid_params_before_http_work(
    monkeypatch,
    capsys,
) -> None:
    def fail_if_client_is_created():
        raise AssertionError("client should not be created for invalid params")

    monkeypatch.setattr(
        "scholarlead_agent.pubmed_main.PubMedClient",
        fail_if_client_is_created,
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "--query",
                "genome assembly",
                "--from-date",
                "2024-12-31",
                "--to-date",
                "2024-01-01",
                "--max-results",
                "10",
            ]
        )

    captured = capsys.readouterr()

    assert error.value.code == 2
    assert "from_date must be earlier than or equal to to_date" in captured.err
    assert "ScholarLead Agent PubMed first-round run completed" not in captured.out
