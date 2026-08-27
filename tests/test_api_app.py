from collections.abc import Iterator
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from scholarlead_agent.api.app import create_app
from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.background_jobs import JOB_TYPE_BATCH_DRAFT
from scholarlead_agent.database import (
    initialize_database,
    insert_pubmed_lead,
    insert_task,
)
from scholarlead_agent.pubmed_models import PubMedLead


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


def test_api_error_format_is_consistent(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    response = client.get("/api/leads/missing-lead")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "LEAD_NOT_FOUND"
    assert body["request_id"]
