from scholarlead_agent.ai.email_draft_quality import (
    FAIL_MISSING_PAPER_GROUNDING,
    FAIL_PAPER_ONLY_CAPABILITY_CLAIM,
    FAIL_UNSUPPORTED_CAPABILITY_CLAIM,
    QUALITY_STATUS_FAIL,
    QUALITY_STATUS_WARNING,
    validate_email_draft_quality,
)
from scholarlead_agent.ai.email_drafts import (
    DRAFT_MODE_CAPABILITY_GROUNDED,
    DRAFT_MODE_PAPER_ONLY,
    EmailDraftInput,
)
from scholarlead_agent.capability_matching import CapabilityMatchItem


def make_input(**overrides: object) -> EmailDraftInput:
    values: dict[str, object] = {
        "lead_id": "lead-1",
        "pi_full_name": "Ada Lovelace",
        "recent_publication_title": "CRISPR imaging in leukemia cells",
        "abstract": "The study uses CRISPR imaging to examine leukemia cells.",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
    }
    values.update(overrides)
    return EmailDraftInput(**values)  # type: ignore[arg-type]


def test_quality_validator_returns_warning_for_non_blocking_style_issues() -> None:
    report = validate_email_draft_quality(
        make_input(),
        subject="Academic exchange on CRISPR imaging",
        body="Dear Ada,\n\nYour CRISPR imaging study is impressive work.\n\nBest regards,\nAlex",
        strict_json_output=True,
    )

    assert report.status == QUALITY_STATUS_WARNING
    assert report.failure_reasons == []
    assert "generic_praise_detected" in report.warnings


def test_quality_validator_rejects_paper_only_capability_claim() -> None:
    report = validate_email_draft_quality(
        make_input(
            draft_mode=DRAFT_MODE_PAPER_ONLY,
            capability_match_status="no_match",
            target_service_type="Single-cell RNA sequencing",
        ),
        subject="Academic exchange on leukemia imaging",
        body="We provide single-cell RNA sequencing for leukemia research.",
        strict_json_output=True,
    )

    assert report.status == QUALITY_STATUS_FAIL
    assert FAIL_PAPER_ONLY_CAPABILITY_CLAIM in report.failure_reasons


def test_quality_validator_rejects_unsupported_capability_claim() -> None:
    crispr = CapabilityMatchItem(
        capability_id="crispr",
        capability_name="CRISPR imaging",
        match_score=0.8,
        match_reason="matched",
        matched_terms=["CRISPR"],
        evidence=["matched term: CRISPR"],
    )
    report = validate_email_draft_quality(
        make_input(
            draft_mode=DRAFT_MODE_CAPABILITY_GROUNDED,
            capability_match_status="partial_match",
            candidate_capabilities=[crispr],
            target_service_type="Spatial transcriptomics",
        ),
        subject="Academic exchange on CRISPR imaging",
        body="We provide spatial transcriptomics for leukemia research.",
        strict_json_output=True,
    )

    assert report.status == QUALITY_STATUS_FAIL
    assert FAIL_UNSUPPORTED_CAPABILITY_CLAIM in report.failure_reasons


def test_quality_validator_rejects_missing_paper_grounding() -> None:
    report = validate_email_draft_quality(
        make_input(),
        subject="Academic exchange on research",
        body="I would like to discuss a project with your group.",
        strict_json_output=True,
    )

    assert report.status == QUALITY_STATUS_FAIL
    assert FAIL_MISSING_PAPER_GROUNDING in report.failure_reasons
