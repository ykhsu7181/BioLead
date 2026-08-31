from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from scholarlead_agent.api.app import create_app
from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.background_jobs import JOB_TYPE_BATCH_DRAFT
from scholarlead_agent.database import (
    insert_email_draft,
    initialize_database,
    insert_pubmed_lead,
    insert_task,
)
from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedPaper


def make_lead(**overrides):
    values = {
        "lead_id": "lead-1",
        "pi_full_name": "Alice Smith",
        "verified_email": "alice@example.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "email_source_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
        "email_source_type": "pubmed_affiliation",
        "name_email_match_confidence": "high",
        "institution": "Example University",
        "country": "United States",
        "country_confidence": "high",
        "recent_publication_title": "Single-cell RNA sequencing in cancer",
        "abstract": "A cancer single-cell RNA sequencing study.",
        "journal": "Example Journal",
        "publication_year": 2026,
        "pmid": "1",
        "doi": None,
        "author_role": "email_author",
        "source_links": ["https://pubmed.ncbi.nlm.nih.gov/1/"],
        "data_quality": "email_evidence_available",
        "manual_review_required": False,
        "notes": "Test lead.",
        "matched_keywords": ["single-cell", "cancer"],
        "target_service_type": "single-cell RNA sequencing",
    }
    values.update(overrides)
    return PubMedLead(**values)


def make_paper() -> PubMedPaper:
    return PubMedPaper(
        source="pubmed",
        pmid="1",
        doi="10.1000/example",
        title="Single-cell RNA sequencing in cancer",
        abstract="A cancer single-cell RNA sequencing study.",
        journal="Example Journal",
        publication_date="2026-01-01",
        publication_year=2026,
        article_types=["Journal Article"],
        mesh_terms=[],
        keywords=["single-cell", "cancer"],
        authors=[
            PubMedAuthor(
                full_name="Alice Smith",
                last_name="Smith",
                fore_name="Alice",
                initials="AS",
                author_position=1,
                is_last_author=True,
                affiliations=["Example University, USA. alice@example.edu"],
            )
        ],
        affiliations=["Example University, USA. alice@example.edu"],
        source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        raw_record_path="data/raw/pubmed/test.xml",
    )


@dataclass(frozen=True)
class FakePubMedRunResult:
    task_id: str
    status: str
    search_params: object
    pmids: list[str]
    papers: list[PubMedPaper]
    leads: list[PubMedLead]
    raw_files: dict[str, str]
    processed_files: dict[str, str]
    run_report_path: Path
    run_report: dict[str, object]
    errors: list[dict[str, str]]
    started_at: str
    finished_at: str


def make_client(db_path: Path) -> TestClient:
    app = create_app()

    def override_database() -> Iterator[sqlite3.Connection]:
        with initialize_database(db_path) as connection:
            yield connection

    app.dependency_overrides[get_database] = override_database
    return TestClient(app)


def test_api_health_and_openapi(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    health = client.get("/api/health")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["success"] is True
    assert health.json()["data"]["status"] == "ok"
    assert openapi.status_code == 200
    assert openapi.json()["info"]["title"] == "ScholarLead Agent API"


def test_api_allows_local_vue_development_origin(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    response = client.options(
        "/api/pubmed/search",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_api_conversation_flow_uses_unified_response(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    created = client.post(
        "/api/conversations",
        json={"conversation_id": "conv-1", "title": "Demo"},
    )
    message = client.post(
        "/api/conversations/conv-1/messages",
        json={"role": "user", "content": "找 PubMed 线索"},
    )
    messages = client.get("/api/conversations/conv-1/messages")

    assert created.json()["data"]["conversation_id"] == "conv-1"
    assert message.json()["data"]["content"] == "找 PubMed 线索"
    assert messages.json()["data"]["total"] == 1
    assert messages.json()["data"]["items"][0]["role"] == "user"


def test_api_jobs_create_get_items_retry(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    created = client.post(
        "/api/jobs",
        json={
            "job_type": JOB_TYPE_BATCH_DRAFT,
            "task_id": "task-1",
            "items": [{"lead_id": "lead-1", "payload": {"rank": 1}}],
        },
    )
    job_id = created.json()["data"]["job_id"]
    job = client.get(f"/api/jobs/{job_id}")
    items = client.get(f"/api/jobs/{job_id}/items")
    retry = client.post(
        f"/api/jobs/{job_id}/retry",
        json={"job_item_id": items.json()["data"]["items"][0]["job_item_id"]},
    )

    assert created.status_code == 200
    assert job.json()["data"]["total_count"] == 1
    assert items.json()["data"]["total"] == 1
    assert retry.status_code == 200
    assert retry.json()["success"] is True


def test_api_leads_and_tasks_read_persisted_database_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "api.sqlite"
    with initialize_database(db_path) as connection:
        insert_task(
            connection,
            task_id="task-1",
            task_type="pubmed",
            status="success",
            query="single-cell cancer",
        )
        insert_pubmed_lead(connection, make_lead(), task_id="task-1")
    client = make_client(db_path)

    leads = client.get("/api/leads")
    lead = client.get("/api/leads/lead-1")
    task = client.get("/api/tasks/task-1")
    task_leads = client.get("/api/tasks/task-1/leads")

    assert leads.json()["data"]["total"] == 1
    assert lead.json()["data"]["lead_id"] == "lead-1"
    assert lead.json()["data"]["payload"]["pi_full_name"] == "Alice Smith"
    assert task.json()["data"]["query"] == "single-cell cancer"
    assert task_leads.json()["data"]["total"] == 1


def test_api_email_draft_review_and_send_boundaries(tmp_path: Path) -> None:
    db_path = tmp_path / "api.sqlite"
    with initialize_database(db_path) as connection:
        insert_pubmed_lead(connection, make_lead())
        draft = build_email_draft(
            evidence=EmailDraftInput(
                lead_id="lead-1",
                pi_full_name="Alice Smith",
                recent_publication_title="Single-cell RNA sequencing in cancer",
                source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
                target_service_type="single-cell RNA sequencing",
                verified_email="alice@example.edu",
                email_status="verified_from_pubmed_affiliation",
            ),
            subject="Question about your single-cell cancer study",
            body="Dear Dr. Smith,\n\nI read your paper.\n\nBest regards,",
            model_name="fake-model",
            generated_at="2026-08-27T10:00:00",
        )
        insert_email_draft(connection, draft, draft_id="draft-1")
    client = make_client(db_path)

    drafts = client.get("/api/email-drafts")
    review = client.post(
        "/api/email-drafts/batch-review",
        json={"draft_ids": ["draft-1"], "reviewer": "Reviewer", "decision": "approve"},
    )
    send = client.post(
        "/api/email-sends/batch-send",
        json={
            "draft_ids": ["draft-1"],
            "actor": "Reviewer",
            "mode": "permission_check",
            "max_items": 1,
        },
    )
    logs = client.get("/api/email-sends")

    assert drafts.json()["data"]["total"] == 1
    workspace = drafts.json()["data"]["items"][0]["reviewer_workspace"]
    assert workspace["paper_evidence"]["title"] == "Single-cell RNA sequencing in cancer"
    assert workspace["quality_report"] == {}
    assert workspace["versions"]["draft_version"] == "v1"
    assert review.json()["data"]["reviewed_count"] == 1
    assert send.json()["data"]["blocked_count"] == 1
    assert logs.json()["data"]["total"] == 1
    assert logs.json()["data"]["items"][0]["status"] == "blocked"


def test_api_pubmed_search_runs_service_and_persists_results(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "api.sqlite"
    client = make_client(db_path)
    calls = []

    def fake_run_pubmed_search(params):
        calls.append(params)
        return FakePubMedRunResult(
            task_id="pubmed-api-test",
            status="success",
            search_params=params,
            pmids=["1"],
            papers=[make_paper()],
            leads=[make_lead()],
            raw_files={"efetch_xml": "data/raw/pubmed/test.xml"},
            processed_files={"papers_csv": "data/processed/pubmed/papers.csv"},
            run_report_path=tmp_path / "run_report.json",
            run_report={
                "task_id": "pubmed-api-test",
                "status": "success",
                "papers_count": 1,
                "leads_count": 1,
            },
            errors=[],
            started_at="2026-08-27T10:00:00",
            finished_at="2026-08-27T10:00:01",
        )

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.pubmed.run_pubmed_search",
        fake_run_pubmed_search,
    )

    response = client.post(
        "/api/pubmed/search",
        json={
            "query": "single-cell cancer",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "max_results": 1,
            "service_type": "single-cell RNA sequencing",
        },
    )

    with initialize_database(db_path) as connection:
        task = connection.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            ("pubmed-api-test",),
        ).fetchone()
        leads = connection.execute("SELECT * FROM leads").fetchall()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["task_id"] == "pubmed-api-test"
    assert data["papers"][0]["title"] == "Single-cell RNA sequencing in cancer"
    assert data["leads"][0]["lead_id"] == "lead-1"
    assert calls[0].query == "single-cell cancer"
    assert task is not None
    assert len(leads) == 1


def test_api_creates_result_package_from_database_task(tmp_path: Path) -> None:
    db_path = tmp_path / "api.sqlite"
    output_dir = tmp_path / "packages"
    with initialize_database(db_path) as connection:
        insert_task(
            connection,
            task_id="task-1",
            task_type="pubmed",
            status="success",
            query="single-cell cancer",
            parameters={"from_date": "2026-01-01", "to_date": "2026-12-31", "max_results": 1},
        )
        insert_pubmed_lead(connection, make_lead(), task_id="task-1")
    client = make_client(db_path)

    response = client.post(
        "/api/result-packages",
        json={"task_id": "task-1", "output_dir": str(output_dir)},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["package_id"] == "TASK_task_1"
    assert data["row_counts"]["customers"] == 1
    assert (output_dir / "TASK_task_1" / "email_send_logs.csv").exists()


def test_api_error_format_is_consistent(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    response = client.get("/api/leads/missing-lead")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "LEAD_NOT_FOUND"
    assert body["request_id"]
