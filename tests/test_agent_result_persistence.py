from dataclasses import dataclass
from pathlib import Path

from scholarlead_agent.agent.loop import AgentRunResult, AgentToolExecution
from scholarlead_agent.agent.tool_types import ToolResult
from scholarlead_agent.database import initialize_database
from scholarlead_agent.pubmed_models import (
    PubMedAuthor,
    PubMedLead,
    PubMedPaper,
    PubMedSearchParams,
)
from scholarlead_agent.services.agent_result_persistence import persist_agent_run_result


@dataclass(frozen=True)
class FakePubMedRunResult:
    task_id: str
    status: str
    search_params: PubMedSearchParams
    papers: list[PubMedPaper]
    leads: list[PubMedLead]
    run_report_path: Path
    run_report: dict[str, object]
    started_at: str
    finished_at: str


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


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="lead-1",
        pi_full_name="Alice Smith",
        verified_email="alice@example.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Example University",
        country="United States",
        country_confidence="high",
        recent_publication_title="Single-cell RNA sequencing in cancer",
        abstract="A cancer single-cell RNA sequencing study.",
        journal="Example Journal",
        publication_year=2026,
        pmid="1",
        doi="10.1000/example",
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/1/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Test lead.",
    )


def make_run_result(tmp_path: Path) -> FakePubMedRunResult:
    return FakePubMedRunResult(
        task_id="pubmed-agent-test",
        status="success",
        search_params=PubMedSearchParams(
            query="single-cell cancer",
            from_date="2026-01-01",
            to_date="2026-12-31",
            max_results=1,
        ),
        papers=[make_paper()],
        leads=[make_lead()],
        run_report_path=tmp_path / "private" / "pubmed_run_report.json",
        run_report={"task_id": "pubmed-agent-test", "status": "success"},
        started_at="2026-08-31T10:00:00",
        finished_at="2026-08-31T10:00:01",
    )


def test_persist_agent_pubmed_result_returns_only_persisted_leads(tmp_path: Path) -> None:
    source_result = make_run_result(tmp_path)
    agent_result = AgentRunResult(
        final_answer="Found one lead.",
        messages=[],
        turns=2,
        tool_executions=[
            AgentToolExecution(
                name="search_pubmed",
                result=ToolResult(
                    success=True,
                    source="pubmed",
                    data={
                        "source": "pubmed",
                        "task_id": source_result.task_id,
                        "leads": [{"lead_id": "lead-1"}],
                        "run_report_path": str(source_result.run_report_path),
                    },
                    persistence_payload=source_result,
                ),
            )
        ],
    )

    with initialize_database(tmp_path / "agent.sqlite") as connection:
        persisted = persist_agent_run_result(connection, agent_result)
        lead = connection.execute(
            "SELECT lead_id FROM leads WHERE lead_id = ?",
            ("lead-1",),
        ).fetchone()

    assert lead is not None
    assert persisted.primary_task_id == "pubmed-agent-test"
    assert persisted.task_ids_by_source == {"pubmed": "pubmed-agent-test"}
    assert persisted.current_turn_lead_ids == ["lead-1"]
    assert persisted.reported_lead_count == 1
    assert persisted.persisted_lead_count == 1
    assert persisted.artifacts == [
        {"source": "pubmed", "kind": "run_report", "name": "pubmed_run_report.json"}
    ]


def test_persist_agent_result_without_internal_payload_does_not_claim_leads(tmp_path: Path) -> None:
    agent_result = AgentRunResult(
        final_answer="Found one lead.",
        messages=[],
        turns=2,
        tool_executions=[
            AgentToolExecution(
                name="search_pubmed",
                result=ToolResult(
                    success=True,
                    source="pubmed",
                    data={"source": "pubmed", "leads": [{"lead_id": "lead-1"}]},
                ),
            )
        ],
    )

    with initialize_database(tmp_path / "agent.sqlite") as connection:
        persisted = persist_agent_run_result(connection, agent_result)

    assert persisted.current_turn_lead_ids == []
    assert persisted.persisted_lead_count == 0
    assert persisted.reported_lead_count == 1
