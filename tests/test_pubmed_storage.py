import json
from pathlib import Path

from scholarlead_agent.pubmed_models import (
    PubMedAuthor,
    PubMedLead,
    PubMedPaper,
    PubMedSearchParams,
)
from scholarlead_agent.pubmed_storage import (
    build_pubmed_processed_output_paths,
    build_pubmed_raw_output_paths,
    build_pubmed_request_meta,
    build_pubmed_run_report,
    build_pubmed_run_report_path,
    save_pubmed_leads_csv,
    save_pubmed_leads_json,
    save_pubmed_papers_csv,
    save_pubmed_papers_json,
    save_pubmed_processed_outputs,
    save_pubmed_efetch_xml,
    save_pubmed_esearch_response,
    save_pubmed_request_meta,
    save_pubmed_run_report,
)


def make_params(raw_dir: Path) -> PubMedSearchParams:
    return PubMedSearchParams(
        query="single cell RNA sequencing cancer",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=25,
        country="US",
        service_type="scRNA-seq",
        raw_dir=raw_dir,
        processed_dir=Path("processed"),
    )


def make_paper(*, pmid: str = "12345678") -> PubMedPaper:
    author = PubMedAuthor(
        full_name="张伟",
        last_name="Zhang",
        fore_name="Wei",
        initials="W",
        author_position=1,
        is_last_author=True,
        affiliations=["Genome Center, Example University, Beijing, China"],
    )
    return PubMedPaper(
        source="pubmed",
        pmid=pmid,
        doi="10.1000/abc",
        title="Single cell RNA sequencing in cancer",
        abstract="中文摘要 with unicode text.",
        journal="A journal",
        publication_date="2024-01-01",
        publication_year=2024,
        article_types=["Journal Article"],
        mesh_terms=["Genomics"],
        keywords=["single cell", "RNA-seq"],
        authors=[author],
        affiliations=author.affiliations,
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
    )


def make_lead(
    *,
    pmid: str = "12345678",
    email: str | None = "zhang.wei@example.edu",
) -> PubMedLead:
    return PubMedLead(
        lead_id=f"lead-{pmid}",
        pi_full_name="张伟",
        verified_email=email,
        email_status="verified_from_pubmed_affiliation" if email else "missing",
        email_source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if email else "missing",
        institution="Example University",
        country="China",
        country_confidence="high",
        recent_publication_title="Single cell RNA sequencing in cancer",
        abstract="中文摘要 with unicode text.",
        journal="A journal",
        publication_year=2024,
        pmid=pmid,
        doi="10.1000/abc",
        author_role="email_author" if email else "candidate_pi_last_author",
        source_links=[f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"],
        data_quality="email_evidence_available" if email else "missing_email_candidate",
        manual_review_required=False if email else True,
        notes="Test lead.",
        country_source="affiliation_text",
        raw_affiliation="Genome Center, Example University, Beijing, China",
        matched_keywords=["single cell", "rna-seq"],
        target_service_type="transcriptome sequencing",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100 if email else 0,
        lead_score=90 if email else 70,
        priority="high" if email else "medium",
        score_explanation="PubMed-only temporary score.",
        funding_activity_score=None,
        funding_activity_reason=(
            "Funding source not connected in PubMed-only first round"
        ),
        outsourcing_tendency_score=None,
        official_scoring_status="pending_multi_source_data",
    )


def test_build_pubmed_raw_output_paths_uses_safe_query_and_timestamp(
    tmp_path: Path,
) -> None:
    paths = build_pubmed_raw_output_paths(
        query=" single-cell RNA sequencing / cancer ",
        raw_dir=tmp_path,
        timestamp="20260817_120000",
    )

    assert paths.esearch_json == (
        tmp_path / "single-cell_RNA_sequencing_cancer_20260817_120000_esearch.json"
    )
    assert paths.efetch_xml == (
        tmp_path / "single-cell_RNA_sequencing_cancer_20260817_120000_efetch.xml"
    )
    assert paths.request_meta_json == (
        tmp_path
        / "single-cell_RNA_sequencing_cancer_20260817_120000_request_meta.json"
    )


def test_save_pubmed_raw_files_and_request_meta(tmp_path: Path) -> None:
    params = make_params(tmp_path)
    paths = build_pubmed_raw_output_paths(
        query=params.query,
        raw_dir=params.raw_dir,
        timestamp="20260817_120000",
    )
    esearch_response = {"esearchresult": {"idlist": ["123", "456"]}}
    efetch_xml = "<PubmedArticleSet><PubmedArticle /></PubmedArticleSet>"

    save_pubmed_esearch_response(esearch_response, paths.esearch_json)
    save_pubmed_efetch_xml(efetch_xml, paths.efetch_xml)
    meta = build_pubmed_request_meta(
        params=params,
        paths=paths,
        collected_at="2026-08-17T10:00:00",
        status="success",
    )
    save_pubmed_request_meta(meta, paths.request_meta_json)

    assert json.loads(paths.esearch_json.read_text(encoding="utf-8")) == (
        esearch_response
    )
    assert paths.efetch_xml.read_text(encoding="utf-8") == efetch_xml

    saved_meta = json.loads(paths.request_meta_json.read_text(encoding="utf-8"))
    assert saved_meta["source"] == "pubmed"
    assert saved_meta["query"] == "single cell RNA sequencing cancer"
    assert saved_meta["from_date"] == "2024-01-01"
    assert saved_meta["to_date"] == "2024-12-31"
    assert saved_meta["max_results"] == 25
    assert saved_meta["country"] == "US"
    assert saved_meta["service_type"] == "scRNA-seq"
    assert saved_meta["collected_at"] == "2026-08-17T10:00:00"
    assert saved_meta["status"] == "success"
    assert saved_meta["raw_files"]["esearch_json"].endswith("_esearch.json")
    assert saved_meta["raw_files"]["efetch_xml"].endswith("_efetch.xml")
    assert saved_meta["errors"] == []


def test_build_pubmed_request_meta_records_failure_errors(tmp_path: Path) -> None:
    params = make_params(tmp_path)
    paths = build_pubmed_raw_output_paths(
        query=params.query,
        raw_dir=params.raw_dir,
        timestamp="20260817_120000",
    )

    meta = build_pubmed_request_meta(
        params=params,
        paths=paths,
        collected_at="2026-08-17T10:00:00",
        status="failed",
        errors=["EFetch HTTP 503"],
    )

    assert meta["status"] == "failed"
    assert meta["errors"] == ["EFetch HTTP 503"]


def test_saved_raw_file_survives_later_processing_error(tmp_path: Path) -> None:
    paths = build_pubmed_raw_output_paths(
        query="genome assembly",
        raw_dir=tmp_path,
        timestamp="20260817_120000",
    )

    save_pubmed_esearch_response({"esearchresult": {"idlist": ["123"]}}, paths.esearch_json)

    try:
        raise RuntimeError("simulated parser failure")
    except RuntimeError:
        pass

    assert paths.esearch_json.exists()
    assert json.loads(paths.esearch_json.read_text(encoding="utf-8")) == {
        "esearchresult": {"idlist": ["123"]}
    }


def test_build_pubmed_processed_output_paths_uses_safe_query_and_timestamp(
    tmp_path: Path,
) -> None:
    paths = build_pubmed_processed_output_paths(
        query=" single-cell RNA sequencing / cancer ",
        processed_dir=tmp_path,
        timestamp="20260817_120000",
    )

    assert paths.papers_json == (
        tmp_path / "pubmed_papers_single-cell_RNA_sequencing_cancer_20260817_120000.json"
    )
    assert paths.papers_csv == (
        tmp_path / "pubmed_papers_single-cell_RNA_sequencing_cancer_20260817_120000.csv"
    )
    assert paths.leads_json == (
        tmp_path / "pubmed_leads_single-cell_RNA_sequencing_cancer_20260817_120000.json"
    )
    assert paths.leads_csv == (
        tmp_path / "pubmed_leads_single-cell_RNA_sequencing_cancer_20260817_120000.csv"
    )


def test_save_pubmed_papers_json_and_csv_are_readable(tmp_path: Path) -> None:
    paper = make_paper()
    json_path = tmp_path / "papers.json"
    csv_path = tmp_path / "papers.csv"

    save_pubmed_papers_json([paper], json_path)
    save_pubmed_papers_csv([paper], csv_path)

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json[0]["pmid"] == "12345678"
    assert saved_json[0]["authors"][0]["full_name"] == "张伟"
    assert saved_json[0]["keywords"] == ["single cell", "RNA-seq"]

    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "张伟" in csv_text
    assert '"single cell"' in csv_text


def test_save_pubmed_leads_json_and_csv_cover_stage13_fields(tmp_path: Path) -> None:
    lead = make_lead()
    json_path = tmp_path / "leads.json"
    csv_path = tmp_path / "leads.csv"

    save_pubmed_leads_json([lead], json_path)
    save_pubmed_leads_csv([lead], csv_path)

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json[0]["pi_full_name"] == "张伟"
    assert saved_json[0]["matched_keywords"] == ["single cell", "rna-seq"]
    assert saved_json[0]["lead_score"] == 90
    assert saved_json[0]["funding_activity_score"] is None
    assert saved_json[0]["official_scoring_status"] == "pending_multi_source_data"

    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "PI_Full_Name,Verified_Email,Email_Status" in csv_text
    assert "张伟" in csv_text
    assert "90" in csv_text
    assert "Funding source not connected in PubMed-only first round" in csv_text


def test_save_pubmed_leads_csv_preserves_missing_and_review_statuses(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "leads.csv"
    lead = make_lead(email=None)

    save_pubmed_leads_csv([lead], csv_path)

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "missing" in csv_text
    assert "missing_email_candidate" in csv_text
    assert "True" in csv_text


def test_save_pubmed_processed_outputs_writes_all_files(tmp_path: Path) -> None:
    paths = build_pubmed_processed_output_paths(
        query="genome assembly",
        processed_dir=tmp_path,
        timestamp="20260817_120000",
    )

    save_pubmed_processed_outputs(
        papers=[make_paper(pmid="1"), make_paper(pmid="2")],
        leads=[make_lead(pmid="1"), make_lead(pmid="2", email=None)],
        paths=paths,
    )

    assert len(json.loads(paths.papers_json.read_text(encoding="utf-8"))) == 2
    assert len(json.loads(paths.leads_json.read_text(encoding="utf-8"))) == 2
    assert paths.papers_csv.exists()
    assert paths.leads_csv.exists()


def test_build_pubmed_run_report_path_uses_safe_query_and_timestamp(
    tmp_path: Path,
) -> None:
    path = build_pubmed_run_report_path(
        query=" single-cell RNA sequencing / cancer ",
        processed_dir=tmp_path,
        timestamp="20260817_120000",
    )

    assert path.run_report_json == (
        tmp_path
        / "pubmed_run_report_single-cell_RNA_sequencing_cancer_20260817_120000.json"
    )


def test_build_pubmed_run_report_success_summary(tmp_path: Path) -> None:
    params = make_params(tmp_path / "raw")
    raw_paths = build_pubmed_raw_output_paths(
        query=params.query,
        raw_dir=params.raw_dir,
        timestamp="20260817_120000",
    )
    processed_paths = build_pubmed_processed_output_paths(
        query=params.query,
        processed_dir=tmp_path / "processed",
        timestamp="20260817_120000",
    )

    report = build_pubmed_run_report(
        params=params,
        task_id="pubmed-20260817-0001",
        pmids=["123", "456", "456"],
        papers=[make_paper(pmid="123"), make_paper(pmid="456")],
        leads=[make_lead(pmid="123"), make_lead(pmid="456", email=None)],
        raw_files=raw_paths,
        processed_files=processed_paths,
        started_at="2026-08-17T10:00:00",
        finished_at="2026-08-17T10:01:00",
        status="success",
    )

    assert report["task_id"] == "pubmed-20260817-0001"
    assert report["source"] == "pubmed"
    assert report["query"] == "single cell RNA sequencing cancer"
    assert report["pmid_count"] == 2
    assert report["paper_count"] == 2
    assert report["lead_count"] == 2
    assert report["leads_with_verified_email_count"] == 1
    assert report["leads_needing_review_count"] == 1
    assert report["missing_email_count"] == 1
    assert report["unknown_country_count"] == 0
    assert report["raw_files"]["esearch_json"].endswith("_esearch.json")
    assert report["processed_files"]["leads_csv"].endswith(".csv")
    assert report["errors"] == []
    assert report["status"] == "success"
    assert report["scoring_mode"] == "pubmed_single_source_temporary"
    assert report["queried_sources"] == ["pubmed"]
    assert report["funding_source_status"] == "not_connected"
    assert report["agent_status"] == "not_enabled_in_first_round"
    assert report["llm_status"] == "not_used_in_first_round"


def test_build_pubmed_run_report_partial_failure_records_error_and_keeps_raw(
    tmp_path: Path,
) -> None:
    params = make_params(tmp_path / "raw")
    raw_paths = build_pubmed_raw_output_paths(
        query=params.query,
        raw_dir=params.raw_dir,
        timestamp="20260817_120000",
    )
    save_pubmed_esearch_response(
        {"esearchresult": {"idlist": ["123"]}},
        raw_paths.esearch_json,
    )

    report = build_pubmed_run_report(
        params=params,
        task_id="pubmed-20260817-partial",
        pmids=["123"],
        papers=[],
        leads=[],
        raw_files=raw_paths,
        processed_files={"papers_json": tmp_path / "processed" / "papers.json"},
        errors=[
            {
                "stage": "efetch",
                "type": "http_error",
                "message": "EFetch HTTP 503",
            }
        ],
        started_at="2026-08-17T10:00:00",
        finished_at="2026-08-17T10:01:00",
        status="partial_failure",
    )

    assert raw_paths.esearch_json.exists()
    assert report["status"] == "partial_failure"
    assert report["pmid_count"] == 1
    assert report["paper_count"] == 0
    assert report["lead_count"] == 0
    assert report["processed_files"]["papers_json"].endswith("papers.json")
    assert report["errors"] == [
        {
            "stage": "efetch",
            "type": "http_error",
            "message": "EFetch HTTP 503",
        }
    ]


def test_build_pubmed_run_report_failed_records_structured_errors(
    tmp_path: Path,
) -> None:
    params = make_params(tmp_path / "raw")

    report = build_pubmed_run_report(
        params=params,
        task_id="pubmed-20260817-failed",
        errors=[
            {
                "stage": "esearch",
                "type": "timeout",
                "message": "ESearch timed out",
            },
            "parser failed before structured error was available",
        ],
        started_at="2026-08-17T10:00:00",
        finished_at="2026-08-17T10:01:00",
        status="failed",
    )

    assert report["status"] == "failed"
    assert report["pmid_count"] == 0
    assert report["paper_count"] == 0
    assert report["lead_count"] == 0
    assert report["raw_files"] == {}
    assert report["processed_files"] == {}
    assert report["errors"][0] == {
        "stage": "esearch",
        "type": "timeout",
        "message": "ESearch timed out",
    }
    assert report["errors"][1] == {
        "stage": "unknown",
        "type": "unknown",
        "message": "parser failed before structured error was available",
    }


def test_save_pubmed_run_report_writes_readable_json(tmp_path: Path) -> None:
    params = make_params(tmp_path / "raw")
    report_path = tmp_path / "run_report.json"
    report = build_pubmed_run_report(
        params=params,
        task_id="pubmed-20260817-save",
        papers=[make_paper()],
        leads=[make_lead()],
        started_at="2026-08-17T10:00:00",
        finished_at="2026-08-17T10:01:00",
        status="success",
    )

    save_pubmed_run_report(report, report_path)

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["task_id"] == "pubmed-20260817-save"
    assert saved_report["lead_count"] == 1
