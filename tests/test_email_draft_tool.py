import json
from typing import Any

from scholarlead_agent.ai.email_drafts import EmailDraft, EmailDraftInput, build_email_draft
from scholarlead_agent.services.email_draft_service import EmailDraftGenerationError
from scholarlead_agent.tools.email_draft_tool import (
    GENERATE_EMAIL_DRAFT_TOOL,
    generate_email_draft,
)


class FakeEmailDraftService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[EmailDraftInput] = []

    def generate(self, evidence: EmailDraftInput) -> EmailDraft:
        self.calls.append(evidence)
        if self.error is not None:
            raise self.error
        return build_email_draft(
            evidence=evidence,
            subject="Collaboration around CRISPR imaging",
            body="Dear Dr. Qi,\n\nI read your recent publication.\n\nBest regards,",
            model_name="fake-email-model",
            generated_at="2026-08-20T10:00:00",
        )


def make_arguments(**overrides: Any) -> dict[str, Any]:
    values = {
        "lead_id": "pubmed-41951915-lei-s-qi",
        "pi_full_name": "Lei S Qi",
        "recent_publication_title": (
            "CRISPR-Cas-based live cell imaging of genome dynamics"
        ),
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/41951915/",
        "target_service_type": "single-cell RNA sequencing",
        "abstract": "Abstract text.",
        "institution": "Stanford University",
        "country": "United States",
        "verified_email": "slqi@stanford.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "pmid": "41951915",
        "doi": "10.1000/example",
        "matched_keywords": ["CRISPR", "genome dynamics"],
    }
    values.update(overrides)
    return values


def test_generate_email_draft_tool_returns_structured_draft() -> None:
    service = FakeEmailDraftService()

    result = generate_email_draft(make_arguments(), service=service)

    assert result.success is True
    assert result.source == "email_draft"
    assert result.data["lead_id"] == "pubmed-41951915-lei-s-qi"
    assert result.data["draft_status"] == "review_pending"
    assert result.data["model_name"] == "fake-email-model"
    assert result.data["can_send"] is False
    assert service.calls[0].matched_keywords == ["CRISPR", "genome dynamics"]


def test_generate_email_draft_tool_preserves_service_and_sender_metadata() -> None:
    service = FakeEmailDraftService()
    result = generate_email_draft(
        make_arguments(
            matched_service_id="single_cell_rna_seq",
            matched_service_name="Single-cell RNA sequencing",
            service_match_score=0.74,
            service_match_reason="Matched single-cell terms.",
            service_matched_terms=["single-cell", "CRISPR"],
            service_match_status="matched",
            service_catalog_version="catalog-v1",
            service_matcher_version="rule-v1",
            sender_profile_version="sender-v1",
            sender_email="alex@example.com",
            sender_signature="Best regards,\nAlex",
        ),
        service=service,
    )

    evidence = result.data["evidence"]

    assert result.success is True
    assert evidence["matched_service"]["service_id"] == "single_cell_rna_seq"
    assert evidence["matched_service"]["match_score"] == 0.74
    assert evidence["sender_profile"]["profile_version"] == "sender-v1"
    assert service.calls[0].service_matched_terms == ["single-cell", "CRISPR"]


def test_generate_email_draft_tool_rejects_missing_required_field() -> None:
    arguments = make_arguments()
    del arguments["target_service_type"]

    result = generate_email_draft(arguments, service=FakeEmailDraftService())

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "target_service_type is required" in (result.error_message or "")


def test_generate_email_draft_tool_converts_generation_failure() -> None:
    result = generate_email_draft(
        make_arguments(),
        service=FakeEmailDraftService(
            error=EmailDraftGenerationError("model returned no email draft content")
        ),
    )

    assert result.success is False
    assert result.error_code == "email_draft_generation_failed"
    assert "no email draft" in (result.error_message or "")


def test_email_draft_tool_schema_has_no_send_action() -> None:
    serialized = json.dumps(GENERATE_EMAIL_DRAFT_TOOL.input_schema)

    assert GENERATE_EMAIL_DRAFT_TOOL.name == "generate_email_draft"
    assert GENERATE_EMAIL_DRAFT_TOOL.effect == "external"
    assert "send" not in GENERATE_EMAIL_DRAFT_TOOL.name
    assert "send_email" not in serialized
