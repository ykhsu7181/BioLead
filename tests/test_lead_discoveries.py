from pathlib import Path
from types import SimpleNamespace

import pytest

import scholarlead_agent.database as database
from scholarlead_agent.database import (
    apply_schema,
    fetch_lead_discoveries,
    fetch_one,
    fetch_task_lead_ids,
    get_schema_version,
    initialize_database,
    insert_pubmed_lead,
    insert_task,
    list_tables,
    persist_pubmed_run_result,
)
from scholarlead_agent.pubmed_models import PubMedLead, PubMedSearchParams


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="pubmed-41951915-lei-s-qi",
        pi_full_name="Lei S Qi",
        verified_email="slqi@stanford.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Stanford University",
        country="United States",
        country_confidence="high",
        recent_publication_title="CRISPR imaging",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_year=2026,
        pmid="41951915",
        doi="10.1000/example",
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/41951915/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Test lead.",
        country_source="affiliation_text",
        raw_affiliation="Stanford University, CA, USA. slqi@stanford.edu.",
        matched_keywords=["CRISPR"],
        target_service_type="single-cell RNA sequencing",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100,
        lead_score=90,
        priority="high",
        score_explanation="PubMed-only temporary score.",
    )


def insert_test_task(connection, task_id: str) -> None:
    insert_task(
        connection,
        task_id=task_id,
        task_type="pubmed_search",
        status="success",
    )


def test_lead_discovery_preserves_multiple_tasks_and_status(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "db.sqlite") as connection:
        insert_test_task(connection, "task-a")
        insert_test_task(connection, "task-b")

        insert_pubmed_lead(
            connection,
            make_lead(),
            task_id="task-a",
            discovered_at="2026-09-01T10:00:00",
        )
        insert_pubmed_lead(
            connection,
            make_lead(),
            task_id="task-b",
            discovered_at="2026-09-02T10:00:00",
        )

        assert fetch_task_lead_ids(connection, "task-a") == [make_lead().lead_id]
        assert fetch_task_lead_ids(connection, "task-b") == [make_lead().lead_id]
        discoveries = fetch_lead_discoveries(connection, make_lead().lead_id)
        latest_pointer = fetch_one(
            connection,
            "SELECT task_id FROM leads WHERE lead_id = ?",
            (make_lead().lead_id,),
        )

    assert [row["discovery_status"] for row in discoveries] == [
        "repeat_record",
        "new_record",
    ]
    assert latest_pointer == {"task_id": "task-b"}


def test_same_task_lead_retry_is_idempotent(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "db.sqlite") as connection:
        insert_test_task(connection, "task-a")
        insert_pubmed_lead(connection, make_lead(), task_id="task-a")
        insert_pubmed_lead(connection, make_lead(), task_id="task-a")
        rows = fetch_lead_discoveries(connection, make_lead().lead_id)

    assert len(rows) == 1
    assert rows[0]["discovery_status"] == "new_record"


def test_v5_lead_pointer_is_backfilled_idempotently(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite"
    with initialize_database(db_path) as connection:
        insert_test_task(connection, "legacy-task")
        insert_pubmed_lead(connection, make_lead(), task_id="legacy-task")
        connection.execute("DROP TABLE lead_discoveries")
        connection.execute("DELETE FROM schema_migrations WHERE version = 6")
        connection.execute("PRAGMA user_version = 5")
        connection.commit()

    with initialize_database(db_path) as connection:
        apply_schema(connection)
        rows = fetch_lead_discoveries(connection, make_lead().lead_id)

    assert len(rows) == 1
    assert rows[0]["source"] == "legacy"
    assert rows[0]["discovery_status"] == "legacy_unknown"


def test_schema_migration_rolls_back_when_backfill_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "legacy.sqlite"
    with initialize_database(db_path) as connection:
        connection.execute("DROP TABLE lead_discoveries")
        connection.execute("DROP TABLE paper_discoveries")
        connection.execute("DELETE FROM schema_migrations WHERE version = 6")
        connection.execute("PRAGMA user_version = 5")
        connection.commit()

        def fail_backfill(_connection) -> None:
            raise RuntimeError("injected migration failure")

        monkeypatch.setattr(database, "_backfill_discovery_history", fail_backfill)
        with pytest.raises(RuntimeError, match="injected migration failure"):
            apply_schema(connection)

        assert get_schema_version(connection) == 5
        assert "lead_discoveries" not in list_tables(connection)
        assert "paper_discoveries" not in list_tables(connection)


def test_pubmed_result_persistence_rolls_back_as_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paper = SimpleNamespace(
        source="pubmed",
        pmid="41951915",
        doi="10.1000/example",
        title="CRISPR imaging",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_date="2026-08-01",
        publication_year=2026,
        authors=[SimpleNamespace(full_name="Lei S Qi")],
        affiliations=["Stanford University, CA, USA."],
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        raw_record_path="data/raw/pubmed/example.xml",
    )
    result = SimpleNamespace(
        task_id="task-failed",
        status="success",
        search_params=PubMedSearchParams(
            query="CRISPR",
            from_date="2026-01-01",
            to_date="2026-09-01",
            max_results=1,
            raw_dir=tmp_path / "raw",
            processed_dir=tmp_path / "processed",
        ),
        papers=[paper],
        leads=[make_lead()],
        run_report_path=tmp_path / "report.json",
        run_report={"status": "success"},
        started_at="2026-09-01T10:00:00",
        finished_at="2026-09-01T10:00:01",
    )

    with initialize_database(tmp_path / "db.sqlite") as connection:
        def fail_report(*args, **kwargs) -> None:
            raise RuntimeError("injected report failure")

        monkeypatch.setattr(database, "insert_run_report", fail_report)
        with pytest.raises(RuntimeError, match="injected report failure"):
            persist_pubmed_run_result(connection, result)

        for table in (
            "tasks",
            "papers",
            "paper_discoveries",
            "leads",
            "lead_discoveries",
            "run_reports",
        ):
            assert fetch_one(
                connection,
                f"SELECT COUNT(*) AS count FROM {table}",
            ) == {"count": 0}
