import json

from scholarlead_agent.agent.model import ModelReply
from scholarlead_agent.ai.email_drafts import DRAFT_MODE_CAPABILITY_GROUNDED
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    PermissionPolicy,
    apply_email_review_decision,
    evaluate_send_permission,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_capabilities import (
    SenderCapability,
    SenderCapabilityCatalog,
    SenderCapabilitySelectionPolicy,
)
from scholarlead_agent.sender_profile import SenderProfile
from scholarlead_agent.service_catalog import CompanyServiceCatalog
from scholarlead_agent.services.email_draft_benchmark import (
    load_email_draft_benchmark,
    run_email_draft_benchmark,
)
from scholarlead_agent.services.email_draft_service import EmailDraftService


class FakeModel:
    def complete(self, *, messages, tools):
        return ModelReply(
            content=json.dumps(
                {
                    "subject": "Academic exchange on single-cell cancer research",
                    "body": (
                        "Dear Alice Smith,\n\n"
                        "I read your single-cell cancer study and its focus on cell states.\n\n"
                        "I lead a team interested in single-cell analysis questions.\n\n"
                        "I would welcome an academic exchange on future directions.\n\n"
                        "Best regards,\nAlex"
                    ),
                }
            ),
            model="benchmark-fake-model",
        )


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="e8-lead-1",
        pi_full_name="Alice Smith",
        verified_email="alice@example.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Example University",
        country="United States",
        country_confidence="high",
        recent_publication_title="Single-cell cancer research",
        abstract="Single-cell analysis characterizes cancer cell states.",
        journal="Example Journal",
        publication_year=2026,
        pmid="1",
        doi=None,
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/1/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Email-E8 acceptance fixture.",
        matched_keywords=["single-cell", "cancer"],
    )


def make_capability_catalog() -> SenderCapabilityCatalog:
    return SenderCapabilityCatalog(
        profile_version="e8-capabilities-v1",
        purpose="Email-E8 test catalog",
        selection_policy=SenderCapabilitySelectionPolicy(
            target_candidate_count=4,
            max_candidate_count=6,
            min_candidate_count=0,
            allow_fewer_when_evidence_is_insufficient=True,
            zero_match_strategy="paper_only",
            llm_may_create_new_capabilities=False,
        ),
        capabilities=[
            SenderCapability(
                capability_id="single_cell",
                capability_name="Single-cell analysis",
                category="Research",
                description="Single-cell analysis",
                positive_keywords=["single-cell"],
                synonyms=["single-cell analysis"],
                research_fields=["cancer"],
                scientific_questions=["cell states"],
                methods=["single-cell analysis"],
            )
        ],
        source_policy={"intended_use": "test"},
        source_path="e8.json",
    )


def test_email_e8_benchmark_has_twenty_labeled_cases_and_passes() -> None:
    version, cases = load_email_draft_benchmark()
    result = run_email_draft_benchmark()

    assert version == "email-e8-fixture-v1"
    assert len(cases) == 20
    assert result.passed is True
    assert result.mode_counts == {
        DRAFT_MODE_CAPABILITY_GROUNDED: 10,
        "paper_only": 10,
    }
    assert result.quality_counts == {"warning": 20}


def test_email_e8_e2e_acceptance_stops_before_provider_send() -> None:
    draft = EmailDraftService(model=FakeModel()).generate_for_lead(
        make_lead(),
        catalog=CompanyServiceCatalog(
            catalog_version="e8-services-v1",
            source_path="e8.csv",
            services=[],
        ),
        sender_profile=SenderProfile(
            profile_version="e8-sender-v1",
            sender_name="Alex",
            sender_title="Research Lead",
            sender_organization="Example Bio",
            signature="Best regards,\nAlex",
            sender_intro_style="i_lead",
        ),
        capability_catalog=make_capability_catalog(),
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(reviewer="Benchmark Reviewer", decision="approve"),
        policy=PermissionPolicy(
            real_email_sending_enabled=False,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
    )
    permission = evaluate_send_permission(
        reviewed,
        policy=PermissionPolicy(
            real_email_sending_enabled=False,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
    )

    assert draft.evidence["draft_mode"] == DRAFT_MODE_CAPABILITY_GROUNDED
    assert draft.evidence["quality_report"]["status"] == "warning"
    assert reviewed["draft_status"] == "review_approved"
    assert permission.allowed is False
    assert "real_email_sending_disabled" in permission.blockers
