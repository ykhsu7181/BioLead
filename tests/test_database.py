import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.ai.model_config import FEATURE_AGENT_REASONING
from scholarlead_agent.ai.usage import AIUsageRecord
from scholarlead_agent.agent.conversation import ConversationMessage, TaskContext
from scholarlead_agent.database import (
    DATABASE_SCHEMA_VERSION,
    EXPECTED_TABLES,
    fetch_conversation_messages,
    fetch_task_context,
    fetch_all,
    fetch_one,
    get_schema_version,
    initialize_database,
    insert_ai_usage_record,
    insert_conversation,
    insert_conversation_message,
    insert_email_draft,
    insert_email_review_record,
    insert_evidence_record,
    insert_pubmed_lead,
    insert_pubmed_paper,
    insert_run_report,
    insert_task,
    insert_tool_call,
    list_tables,
    persist_pubmed_run_result,
    upsert_conversation_state,
)
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    apply_email_review_decision,
    build_email_audit_record,
    evaluate_send_permission,
)
from scholarlead_agent.pubmed_models import (
    PubMedAuthor,
    PubMedLead,
    PubMedPaper,
    PubMedSearchParams,
)
from scholarlead_agent.unified_models import EvidenceRecord


def make_paper() -> PubMedPaper:
    author = PubMedAuthor(
        full_name="Lei S Qi",
        last_name="Qi",
        fore_name="Lei S",
        initials="LSQ",
        author_position=1,
        is_last_author=True,
        affiliations=["Stanford University, Stanford, CA, USA. slqi@stanford.edu."],
    )
    return PubMedPaper(
        source="pubmed",
        pmid="41951915",
        doi="10.1000/example",
        title="CRISPR-Cas-based live cell imaging of genome dynamics",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_date="2026-08-01",
        publication_year=2026,
        article_types=["Journal Article"],
        mesh_terms=["Genome"],
        keywords=["CRISPR"],
        authors=[author],
        affiliations=author.affiliations,
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
    )


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
        recent_publication_title="CRISPR-Cas-based live cell imaging of genome dynamics",
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
        raw_affiliation="Stanford University, Stanford, CA, USA. slqi@stanford.edu.",
        matched_keywords=["CRISPR"],
        target_service_type="single-cell RNA sequencing",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100,
        lead_score=90,
        priority="high",
        score_explanation="PubMed-only temporary score.",
    )


def make_email_draft():
    return build_email_draft(
        evidence=EmailDraftInput(
            lead_id="pubmed-41951915-lei-s-qi",
            pi_full_name="Lei S Qi",
            recent_publication_title="CRISPR-Cas-based live cell imaging of genome dynamics",
            source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
            target_service_type="single-cell RNA sequencing",
            verified_email="slqi@stanford.edu",
            email_status="verified_from_pubmed_affiliation",
        ),
        subject="Collaboration around CRISPR imaging",
        body="Dear Dr. Qi,\n\nI read your recent paper.\n\nBest regards,",
        model_name="fake-email-model",
        generated_at="2026-08-24T10:00:00",
    )


def test_initialize_database_creates_expected_tables_and_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "scholarlead.sqlite"

    with initialize_database(db_path) as connection:
        assert get_schema_version(connection) == DATABASE_SCHEMA_VERSION
        assert EXPECTED_TABLES.issubset(list_tables(connection))

    assert db_path.exists()


def test_initialize_database_rejects_empty_task_id(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            insert_task(
                connection,
                task_id="",
                task_type="pubmed_search",
                status="failed",
            )


def test_database_can_store_pubmed_task_paper_lead_and_report(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        insert_task(
            connection,
            task_id="task-1",
            task_type="pubmed_search",
            query="CRISPR genome dynamics",
            status="success",
            parameters={"max_results": 5},
            started_at="2026-08-24T10:00:00",
            finished_at="2026-08-24T10:00:01",
            run_report_path="data/processed/pubmed/run_report.json",
        )
        insert_pubmed_paper(connection, make_paper(), task_id="task-1")
        insert_pubmed_lead(connection, make_lead(), task_id="task-1")
        insert_run_report(
            connection,
            report_id="report-1",
            task_id="task-1",
            source="pubmed",
            status="success",
            run_report_path="data/processed/pubmed/run_report.json",
            report={"paper_count": 1, "lead_count": 1},
        )

        task = fetch_one(connection, "SELECT * FROM tasks WHERE task_id = ?", ("task-1",))
        paper = fetch_one(
            connection,
            "SELECT * FROM papers WHERE paper_id = ?",
            ("pubmed:41951915",),
        )
        lead = fetch_one(
            connection,
            "SELECT * FROM leads WHERE lead_id = ?",
            ("pubmed-41951915-lei-s-qi",),
        )
        report = fetch_one(
            connection,
            "SELECT * FROM run_reports WHERE report_id = ?",
            ("report-1",),
        )

    assert task is not None
    assert json.loads(task["parameters_json"]) == {"max_results": 5}
    assert paper is not None
    assert paper["title"].startswith("CRISPR-Cas")
    assert json.loads(paper["authors_json"]) == ["Lei S Qi"]
    assert lead is not None
    assert lead["verified_email"] == "slqi@stanford.edu"
    assert lead["manual_review_required"] == 0
    assert json.loads(lead["payload_json"])["lead_id"] == "pubmed-41951915-lei-s-qi"
    assert report is not None
    assert json.loads(report["report_json"]) == {"lead_count": 1, "paper_count": 1}


def test_database_can_store_conversation_messages_and_task_context(tmp_path: Path) -> None:
    db_path = tmp_path / "scholarlead.sqlite"
    with initialize_database(db_path) as connection:
        insert_conversation(
            connection,
            conversation_id="conv-1",
            title="single-cell cancer",
            status="active",
        )
        insert_conversation_message(
            connection,
            ConversationMessage(
                message_id="msg-1",
                conversation_id="conv-1",
                role="user",
                content="Find leads.",
                created_at="2026-08-26T10:00:00Z",
            ),
        )
        insert_conversation_message(
            connection,
            ConversationMessage(
                message_id="msg-2",
                conversation_id="conv-1",
                role="assistant",
                content="Found leads.",
                created_at="2026-08-26T10:00:01Z",
                metadata={"turns": 2},
            ),
        )
        upsert_conversation_state(
            connection,
            TaskContext(
                conversation_id="conv-1",
                task_id="task-1",
                last_run_report_path="report.json",
                last_lead_ids=["lead-1", "lead-2"],
                last_selected_lead_ids=["lead-1"],
                updated_at="2026-08-26T10:00:02Z",
            ),
        )

    with initialize_database(db_path) as connection:
        messages = fetch_conversation_messages(connection, "conv-1")
        context = fetch_task_context(connection, "conv-1")
        other_context = fetch_task_context(connection, "conv-other")

    assert [message.content for message in messages] == ["Find leads.", "Found leads."]
    assert messages[1].metadata == {"turns": 2}
    assert context is not None
    assert context.task_id == "task-1"
    assert context.last_lead_ids == ["lead-1", "lead-2"]
    assert context.last_selected_lead_ids == ["lead-1"]
    assert other_context is None


def test_database_can_store_evidence_email_review_ai_usage_and_tool_call(
    tmp_path: Path,
) -> None:
    draft = make_email_draft()
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-24T10:05:00",
        ),
    )
    permission = evaluate_send_permission(reviewed)
    audit = build_email_audit_record(
        event_type="email_review_decision",
        lead_id="pubmed-41951915-lei-s-qi",
        actor="Reviewer",
        status_before="review_pending",
        status_after="review_approved",
        permission=permission,
        occurred_at="2026-08-24T10:06:00",
        event_id="event-1",
    )
    usage = AIUsageRecord(
        usage_id="usage-1",
        account_alias="test-account",
        provider="openai_compatible",
        called_at="2026-08-24T10:00:00",
        feature_module=FEATURE_AGENT_REASONING,
        model_name="model",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        estimated_cost=None,
        currency=None,
        pricing_config_version="test",
        status="success",
        error_type=None,
        error_message=None,
        task_id="task-1",
        lead_id=None,
        started_at="2026-08-24T10:00:00",
        finished_at="2026-08-24T10:00:01",
        latency_ms=1000,
    )
    evidence = EvidenceRecord(
        source_name="pubmed",
        source_type="pubmed_lead",
        source_id="pubmed-41951915-lei-s-qi",
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        retrieved_at="2026-08-24T10:00:00",
        field_name="verified_email",
        field_value="slqi@stanford.edu",
        confidence="high",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
        note="PubMed affiliation text",
    )

    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        insert_task(
            connection,
            task_id="task-1",
            task_type="agent_task",
            status="success",
        )
        insert_pubmed_lead(connection, make_lead(), task_id="task-1")
        evidence_id = insert_evidence_record(
            connection,
            evidence,
            evidence_id="evidence-1",
        )
        draft_id = insert_email_draft(connection, reviewed, draft_id="draft-1")
        insert_email_review_record(connection, audit)
        insert_ai_usage_record(connection, usage)
        insert_tool_call(
            connection,
            tool_call_id="tool-call-1",
            task_id="task-1",
            tool_name="search_pubmed",
            source="pubmed",
            success=True,
            arguments={"query": "CRISPR"},
            result={"paper_count": 1},
            started_at="2026-08-24T10:00:00",
            finished_at="2026-08-24T10:00:01",
        )

        rows = {
            "evidence": fetch_one(
                connection,
                "SELECT * FROM evidence_records WHERE evidence_id = ?",
                (evidence_id,),
            ),
            "draft": fetch_one(
                connection,
                "SELECT * FROM email_drafts WHERE draft_id = ?",
                (draft_id,),
            ),
            "review": fetch_one(
                connection,
                "SELECT * FROM email_reviews WHERE event_id = ?",
                ("event-1",),
            ),
            "usage": fetch_one(
                connection,
                "SELECT * FROM ai_usage WHERE usage_id = ?",
                ("usage-1",),
            ),
            "tool_call": fetch_one(
                connection,
                "SELECT * FROM tool_calls WHERE tool_call_id = ?",
                ("tool-call-1",),
            ),
        }

    assert rows["evidence"] is not None
    assert rows["evidence"]["field_name"] == "verified_email"
    assert rows["draft"] is not None
    assert rows["draft"]["draft_status"] == "review_approved"
    assert rows["draft"]["can_send"] == 0
    assert rows["review"] is not None
    assert "real_email_sending_disabled" in json.loads(
        rows["review"]["permission_blockers_json"]
    )
    assert rows["usage"] is not None
    assert rows["usage"]["total_tokens"] == 15
    assert rows["tool_call"] is not None
    assert json.loads(rows["tool_call"]["arguments_json"]) == {"query": "CRISPR"}


def test_fetch_all_returns_plain_dict_rows(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        insert_task(connection, task_id="task-1", task_type="pubmed", status="success")
        insert_task(connection, task_id="task-2", task_type="agent", status="failed")

        rows = fetch_all(connection, "SELECT task_id FROM tasks ORDER BY task_id")

    assert rows == [{"task_id": "task-1"}, {"task_id": "task-2"}]


def test_persist_pubmed_run_result_writes_core_tables(tmp_path: Path) -> None:
    result = SimpleNamespace(
        task_id="pubmed-task-1",
        status="success",
        search_params=PubMedSearchParams(
            query="CRISPR genome dynamics",
            from_date="2026-01-01",
            to_date="2026-08-24",
            max_results=1,
            raw_dir=tmp_path / "raw",
            processed_dir=tmp_path / "processed",
        ),
        papers=[make_paper()],
        leads=[make_lead()],
        run_report_path=tmp_path / "processed" / "run_report.json",
        run_report={"status": "success", "paper_count": 1, "lead_count": 1},
        started_at="2026-08-24T10:00:00",
        finished_at="2026-08-24T10:00:01",
    )

    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        persist_pubmed_run_result(connection, result)

        task = fetch_one(
            connection,
            "SELECT * FROM tasks WHERE task_id = ?",
            ("pubmed-task-1",),
        )
        paper_count = fetch_one(connection, "SELECT COUNT(*) AS count FROM papers")
        lead_count = fetch_one(connection, "SELECT COUNT(*) AS count FROM leads")
        lead_discovery = fetch_one(
            connection,
            "SELECT * FROM lead_discoveries WHERE task_id = ?",
            ("pubmed-task-1",),
        )
        paper_discovery = fetch_one(
            connection,
            "SELECT * FROM paper_discoveries WHERE task_id = ?",
            ("pubmed-task-1",),
        )
        report = fetch_one(
            connection,
            "SELECT * FROM run_reports WHERE report_id = ?",
            ("pubmed-task-1:run_report",),
        )

    assert task is not None
    params = json.loads(task["parameters_json"])
    assert params["raw_dir"].endswith("raw")
    assert paper_count == {"count": 1}
    assert lead_count == {"count": 1}
    assert lead_discovery is not None
    assert lead_discovery["discovered_at"] == "2026-08-24T10:00:01"
    assert lead_discovery["discovery_status"] == "new_record"
    assert paper_discovery is not None
    assert paper_discovery["discovered_at"] == "2026-08-24T10:00:01"
    assert report is not None
    assert json.loads(report["report_json"])["lead_count"] == 1
