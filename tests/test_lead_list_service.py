from pathlib import Path

import pytest

from scholarlead_agent.database import (
    initialize_database,
    insert_email_draft,
    insert_pubmed_lead,
    insert_task,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.services.lead_list_service import (
    LeadListQuery,
    fetch_lead_filter_options,
    query_leads,
)


def make_lead(
    lead_id: str,
    *,
    name: str,
    country: str,
    keywords: list[str],
    email: str | None = None,
) -> PubMedLead:
    return PubMedLead(
        lead_id=lead_id,
        pi_full_name=name,
        verified_email=email,
        email_status="verified_from_pubmed_affiliation" if email else "missing",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if email else "unknown",
        institution="Example University",
        country=country,
        country_confidence="high",
        recent_publication_title="Single-cell cancer study",
        abstract="Abstract.",
        journal="Journal",
        publication_year=2026,
        pmid=lead_id,
        doi=None,
        author_role="email_author",
        source_links=[f"https://pubmed.ncbi.nlm.nih.gov/{lead_id}/"],
        data_quality="email_evidence_available" if email else "missing_email_candidate",
        manual_review_required=not bool(email),
        notes="Test.",
        matched_keywords=keywords,
    )


def seed_leads(connection) -> None:
    for task_id in ("task-a", "task-b"):
        insert_task(
            connection,
            task_id=task_id,
            task_type="pubmed_search",
            status="success",
            query=f"query {task_id}",
        )
    lead_a = make_lead(
        "lead-a",
        name="Alice Smith",
        country="United States",
        keywords=["single-cell", "cancer"],
        email="alice@example.edu",
    )
    insert_pubmed_lead(connection, lead_a, task_id="task-a", discovered_at="2026-09-01")
    insert_pubmed_lead(connection, lead_a, task_id="task-b", discovered_at="2026-09-02")
    insert_pubmed_lead(
        connection,
        make_lead(
            "lead-b",
            name="Bob Chen",
            country="China",
            keywords=["CRISPR"],
        ),
        task_id="task-b",
        discovered_at="2026-09-03",
    )


def test_lead_list_returns_business_dto_and_stable_current_scope(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        seed_leads(connection)
        result = query_leads(
            connection,
            LeadListQuery(scope="current", task_id="task-a"),
        )

    assert result.total == 1
    assert result.scope_total == 1
    assert result.all_total == 2
    item = result.items[0]
    assert item["lead_id"] == "lead-a"
    assert item["email_display_status"] == "verified"
    assert item["contact_status"] == "not_contacted"
    assert item["current_task_match"] is True
    assert item["discovery_count"] == 2
    assert item["research_topics"] == ["single-cell", "cancer"]
    assert item["latest_task_id"] == "task-b"


def test_lead_list_filters_before_counting_and_pagination(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        seed_leads(connection)
        insert_email_draft(
            connection,
            {"lead_id": "lead-a", "draft_status": "review_approved"},
            draft_id="draft-a",
        )
        result = query_leads(
            connection,
            LeadListQuery(
                country="United States",
                research="single-cell",
                email_status="verified",
                contact_status="ready_to_send",
                source="pubmed",
            ),
        )

    assert result.total == 1
    assert result.scope_total == 2
    assert result.items[0]["lead_id"] == "lead-a"
    assert result.items[0]["matched_source"] == "pubmed"


def test_like_wildcards_are_treated_as_literal_search_text(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        seed_leads(connection)
        result = query_leads(connection, LeadListQuery(query="%"))

    assert result.total == 0


def test_invalid_payload_does_not_break_research_filter_or_options(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        seed_leads(connection)
        connection.execute(
            "UPDATE leads SET payload_json = 'not-json' WHERE lead_id = 'lead-b'"
        )
        connection.commit()
        result = query_leads(connection, LeadListQuery(research="single-cell"))
        options = fetch_lead_filter_options(connection)

    assert [item["lead_id"] for item in result.items] == ["lead-a"]
    assert options["countries"] == ["China", "United States"]
    assert options["sources"] == ["pubmed"]
    assert "single-cell" in options["research_topics"]


def test_current_scope_requires_a_persisted_task(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        with pytest.raises(ValueError, match="task_id is required"):
            query_leads(connection, LeadListQuery(scope="current"))
        with pytest.raises(ValueError, match="persisted task"):
            query_leads(
                connection,
                LeadListQuery(scope="current", task_id="missing"),
            )


def test_lead_list_applies_database_pagination_with_stable_counts(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "leads.sqlite") as connection:
        insert_task(
            connection,
            task_id="task-page",
            task_type="pubmed_search",
            status="success",
        )
        for index in range(25):
            insert_pubmed_lead(
                connection,
                make_lead(
                    f"lead-{index:02d}",
                    name=f"Researcher {index:02d}",
                    country="Canada",
                    keywords=["genomics"],
                ),
                task_id="task-page",
                discovered_at=f"2026-09-03T10:{index:02d}:00",
            )

        result = query_leads(
            connection,
            LeadListQuery(
                page=2,
                page_size=20,
                scope="current",
                task_id="task-page",
                sort_by="name",
                sort_dir="asc",
            ),
        )

    assert result.total == 25
    assert result.scope_total == 25
    assert len(result.items) == 5
    assert result.items[0]["pi_full_name"] == "Researcher 20"
