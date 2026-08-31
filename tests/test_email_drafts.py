import json
from typing import Any

import pytest

from scholarlead_agent.ai.email_drafts import (
    DRAFT_MODE_PAPER_ONLY,
    EMAIL_DRAFT_PROMPT_VERSION_V2,
    DRAFT_STATUS_REVIEW_PENDING,
    EmailDraftInput,
    build_email_draft_evidence,
    build_email_draft_input_from_lead,
    build_email_draft_messages,
    email_draft_to_dict,
    parse_email_draft_model_output,
)
from scholarlead_agent.agent.model import ModelReply
from scholarlead_agent.capability_matching import CapabilityMatchItem
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_capabilities import (
    SenderCapability,
    SenderCapabilityCatalog,
    SenderCapabilitySelectionPolicy,
)
from scholarlead_agent.sender_profile import SenderProfile
from scholarlead_agent.service_catalog import CompanyService, CompanyServiceCatalog
from scholarlead_agent.services.email_draft_service import (
    EmailDraftGenerationError,
    EmailDraftService,
    build_auto_email_draft_input_from_lead,
)


class FakeModel:
    def __init__(
        self,
        *,
        reply: ModelReply | None = None,
        replies: list[ModelReply] | None = None,
        error: Exception | None = None,
    ) -> None:
        default_reply = reply or ModelReply(
            content=json.dumps(
                {
                    "subject": "Exploring single-cell research collaboration",
                    "body": (
                        "Dear Dr. Qi,\n\n"
                        "I read your recent publication on CRISPR-based live cell "
                        "imaging of genome dynamics. Your work appears closely "
                        "related to single-cell analysis, and I wondered whether "
                        "our scRNA-seq support could be useful for future studies.\n\n"
                        "Best regards,\nScholarLead"
                    ),
                }
            ),
            model="fake-email-model",
        )
        self.replies = list(replies or [default_reply])
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.calls.append({"messages": messages, "tools": tools})
        if self.error is not None:
            raise self.error
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


def make_input(**overrides: Any) -> EmailDraftInput:
    values = {
        "lead_id": "pubmed-41951915-lei-s-qi",
        "pi_full_name": "Lei S Qi",
        "recent_publication_title": (
            "CRISPR-Cas-based live cell imaging of genome dynamics"
        ),
        "abstract": "The study describes live cell imaging of genome dynamics.",
        "institution": "Stanford University",
        "country": "United States",
        "verified_email": "slqi@stanford.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "pmid": "41951915",
        "doi": "10.1000/example",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/41951915/",
        "matched_keywords": ["CRISPR", "genome dynamics"],
        "target_service_type": "single-cell RNA sequencing",
        "sender_name": "Alex",
        "sender_title": "Research Partnership",
        "organization_name": "ScholarLead",
        "service_context": "support for transcriptomics study design",
    }
    values.update(overrides)
    return EmailDraftInput(**values)


def make_lead(**overrides: Any) -> PubMedLead:
    values = {
        "lead_id": "pubmed-41951915-lei-s-qi",
        "pi_full_name": "Lei S Qi",
        "verified_email": "slqi@stanford.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "email_source_url": "https://pubmed.ncbi.nlm.nih.gov/41951915/",
        "email_source_type": "pubmed_affiliation",
        "name_email_match_confidence": "high",
        "institution": "Stanford University",
        "country": "United States",
        "country_confidence": "high",
        "recent_publication_title": (
            "CRISPR-Cas-based live cell imaging of genome dynamics"
        ),
        "abstract": "The study describes live cell imaging of genome dynamics.",
        "journal": "Example Journal",
        "publication_year": 2026,
        "pmid": "41951915",
        "doi": "10.1000/example",
        "author_role": "email_author",
        "source_links": ["https://pubmed.ncbi.nlm.nih.gov/41951915/"],
        "data_quality": "email_evidence_available",
        "manual_review_required": False,
        "notes": "Test lead.",
        "matched_keywords": ["CRISPR"],
        "target_service_type": "single-cell RNA sequencing",
    }
    values.update(overrides)
    return PubMedLead(**values)


def make_catalog() -> CompanyServiceCatalog:
    return CompanyServiceCatalog(
        catalog_version="catalog-v1",
        source_path="test.csv",
        services=[
            CompanyService(
                catalog_version="catalog-v1",
                updated_at="2026-08-26",
                service_id="single_cell_rna_seq",
                service_name="Single-cell RNA sequencing",
                service_category="sequencing",
                description="Single-cell RNA sequencing services",
                positive_keywords=["single-cell", "CRISPR"],
                synonyms=["scRNA-seq"],
                application_fields=["genome dynamics"],
                supported_organisms=["human"],
                company_capability="Single-cell profiling support",
                selling_points="Resolve cell heterogeneity",
                email_talking_points="Connect imaging findings with cell states",
                enabled=True,
            )
        ],
    )


def make_sender_profile() -> SenderProfile:
    return SenderProfile(
        profile_version="sender-v1",
        sender_name="Alex Chen",
        sender_title="Research Partnership Manager",
        sender_organization="Example Bio",
        sender_email="alex@example.com",
        signature="Best regards,\nAlex",
    )


def make_capability_catalog(*capabilities: SenderCapability) -> SenderCapabilityCatalog:
    return SenderCapabilityCatalog(
        profile_version="capabilities-v1",
        purpose="Test sender capabilities",
        selection_policy=SenderCapabilitySelectionPolicy(
            target_candidate_count=4,
            max_candidate_count=6,
            min_candidate_count=0,
            allow_fewer_when_evidence_is_insufficient=True,
            zero_match_strategy="paper_only",
            llm_may_create_new_capabilities=False,
        ),
        capabilities=list(capabilities),
        source_policy={"intended_use": "test"},
        source_path="capabilities.json",
    )


def make_capability(capability_id: str, term: str) -> SenderCapability:
    return SenderCapability(
        capability_id=capability_id,
        capability_name=capability_id.replace("_", " ").title(),
        category="Test",
        description="Test capability",
        positive_keywords=[term],
        synonyms=[f"{term} synonym"],
        research_fields=[f"{term} field"],
        scientific_questions=[f"How does {term} work?"],
        methods=[f"{term} method"],
        enabled=True,
    )


def test_build_email_draft_messages_uses_evidence_and_no_api_key() -> None:
    messages = build_email_draft_messages(make_input())
    prompt = "\n".join(message["content"] for message in messages)

    assert "CRISPR-Cas-based live cell imaging" in prompt
    assert "funding_evidence" in prompt
    assert "no funding evidence is provided" in prompt
    assert "OPENAI_API_KEY" not in prompt
    assert "sk-" not in prompt


def test_prompt_v2_uses_academic_cold_email_rules_and_safe_greeting() -> None:
    messages = build_email_draft_messages(make_input(sender_intro_style="i_lead"))
    system_prompt = messages[0]["content"]
    prompt = messages[1]["content"]

    assert "three concise paragraphs" in system_prompt
    assert "Academic exchange on" in system_prompt
    assert "I lead" in system_prompt
    assert '"greeting": "Dear Lei S Qi,"' in prompt
    assert '"sender_intro_style": "i_lead"' in prompt
    assert f'"email_prompt_version": "{EMAIL_DRAFT_PROMPT_VERSION_V2}"' in prompt


def test_prompt_v2_hides_service_and_capability_claims_for_paper_only() -> None:
    messages = build_email_draft_messages(
        make_input(
            draft_mode=DRAFT_MODE_PAPER_ONLY,
            capability_match_status="no_match",
            target_service_type="Single-cell RNA sequencing",
            service_context="Single-cell profiling support",
            matched_service_name="Single-cell RNA sequencing",
        )
    )
    prompt = messages[1]["content"]

    assert '"draft_mode": "paper_only"' in prompt
    assert '"matched_service": null' in prompt
    assert '"candidate_capabilities": []' in prompt
    assert "Single-cell RNA sequencing" not in prompt
    assert "Single-cell profiling support" not in prompt


def test_email_draft_input_rejects_unsupported_sender_intro_style() -> None:
    with pytest.raises(ValueError, match="sender_intro_style is not supported"):
        build_email_draft_evidence(make_input(sender_intro_style="invented_style"))


def test_email_draft_service_generates_structured_review_pending_draft() -> None:
    model = FakeModel()
    draft = EmailDraftService(model=model).generate(make_input())
    data = email_draft_to_dict(draft)

    assert draft.lead_id == "pubmed-41951915-lei-s-qi"
    assert draft.language == "en"
    assert draft.draft_status == DRAFT_STATUS_REVIEW_PENDING
    assert draft.model_name == "fake-email-model"
    assert draft.source_pmid == "41951915"
    assert draft.source_url == "https://pubmed.ncbi.nlm.nih.gov/41951915/"
    assert draft.can_send is False
    assert "human_review_required" in draft.warnings
    assert data["subject"] == "Exploring single-cell research collaboration"
    assert model.calls[0]["tools"] == []


def test_email_draft_without_abstract_and_verified_email_still_generates_review_draft() -> None:
    draft = EmailDraftService(model=FakeModel()).generate(
        make_input(abstract=None, verified_email=None, email_status="missing")
    )

    assert draft.can_send is False
    assert draft.draft_status == "review_pending"
    assert "missing_verified_email" in draft.warnings
    assert "missing_abstract" in draft.warnings
    assert draft.verified_email is None


def test_build_input_from_lead_preserves_source_evidence() -> None:
    evidence = build_email_draft_input_from_lead(
        make_lead(),
        sender_name="Alex",
        service_context="genomics support",
    )

    data = build_email_draft_evidence(evidence)

    assert evidence.pi_full_name == "Lei S Qi"
    assert evidence.source_url == "https://pubmed.ncbi.nlm.nih.gov/41951915/"
    assert evidence.verified_email == "slqi@stanford.edu"
    assert data["funding_evidence"] is None


def test_auto_email_draft_input_uses_service_match_and_sender_profile() -> None:
    evidence = build_auto_email_draft_input_from_lead(
        make_lead(),
        catalog=make_catalog(),
        sender_profile=make_sender_profile(),
        capability_catalog=make_capability_catalog(make_capability("crispr", "CRISPR")),
    )
    data = build_email_draft_evidence(evidence)

    assert evidence.target_service_type == "Single-cell RNA sequencing"
    assert evidence.sender_name == "Alex Chen"
    assert evidence.sender_title == "Research Partnership Manager"
    assert evidence.organization_name == "Example Bio"
    assert evidence.matched_service_id == "single_cell_rna_seq"
    assert evidence.service_catalog_version == "catalog-v1"
    assert evidence.sender_profile_version == "sender-v1"
    assert "Service match reason" in (evidence.service_context or "")
    assert data["matched_service"]["service_name"] == "Single-cell RNA sequencing"
    assert data["sender_profile"]["profile_version"] == "sender-v1"
    assert evidence.draft_mode == "capability_grounded"
    assert data["capability_match"]["status"] == "partial_match"
    assert data["capability_match"]["candidate_capabilities"][0]["capability_id"] == "crispr"


def test_auto_email_draft_input_uses_capability_match_when_no_service_matches() -> None:
    catalog = CompanyServiceCatalog(
        catalog_version="catalog-v1",
        source_path="test.csv",
        services=[
            CompanyService(
                catalog_version="catalog-v1",
                updated_at="2026-08-26",
                service_id="spatial",
                service_name="Spatial transcriptomics",
                service_category="spatial",
                description="Spatial services",
                positive_keywords=["spatial transcriptomics"],
                enabled=True,
            )
        ],
    )

    evidence = build_auto_email_draft_input_from_lead(
        make_lead(),
        catalog=catalog,
        sender_profile=make_sender_profile(),
        capability_catalog=make_capability_catalog(make_capability("crispr", "CRISPR")),
    )

    assert evidence.matched_service_id is None
    assert evidence.target_service_type == ""
    assert evidence.capability_match_status == "partial_match"
    assert evidence.draft_mode == "capability_grounded"
    assert [item.capability_id for item in evidence.candidate_capabilities] == ["crispr"]


def test_auto_email_draft_input_uses_paper_only_when_no_capability_matches() -> None:
    catalog = CompanyServiceCatalog(
        catalog_version="catalog-v1",
        source_path="test.csv",
        services=[],
    )
    evidence = build_auto_email_draft_input_from_lead(
        make_lead(recent_publication_title="Clinical case report", abstract=""),
        catalog=catalog,
        sender_profile=make_sender_profile(),
        capability_catalog=make_capability_catalog(
            make_capability("spatial", "spatial transcriptomics")
        ),
    )
    data = build_email_draft_evidence(evidence)

    assert evidence.matched_service_id is None
    assert evidence.capability_match_status == "no_match"
    assert evidence.candidate_capabilities == []
    assert evidence.draft_mode == "paper_only"
    assert data["draft_mode"] == "paper_only"
    assert data["capability_match"]["candidate_capabilities"] == []


def test_email_draft_input_accepts_empty_legacy_target_service_type() -> None:
    evidence = make_input(target_service_type="")

    normalized = build_email_draft_evidence(evidence)

    assert normalized["target_service_type"] == ""
    assert normalized["draft_mode"] == "legacy_service_based"


def test_email_draft_input_rejects_capabilities_for_no_match() -> None:
    capability = CapabilityMatchItem(
        capability_id="crispr",
        capability_name="CRISPR",
        match_score=0.5,
        match_reason="matched",
        matched_terms=["CRISPR"],
        evidence=["matched term: CRISPR"],
    )

    with pytest.raises(ValueError, match="no_match cannot include candidate capabilities"):
        build_email_draft_evidence(
            make_input(
                capability_match_status="no_match",
                candidate_capabilities=[capability],
            )
        )


def test_email_draft_service_generate_for_lead_adds_traceable_match_evidence() -> None:
    model = FakeModel()
    draft = EmailDraftService(model=model).generate_for_lead(
        make_lead(),
        catalog=make_catalog(),
        sender_profile=make_sender_profile(),
        capability_catalog=make_capability_catalog(make_capability("crispr", "CRISPR")),
    )
    prompt = model.calls[0]["messages"][1]["content"]

    assert draft.target_service_type == "Single-cell RNA sequencing"
    assert draft.evidence["matched_service"]["service_id"] == "single_cell_rna_seq"
    assert draft.evidence["sender_profile"]["profile_version"] == "sender-v1"
    assert "matched_service" in prompt
    assert "Single-cell RNA sequencing" in prompt


def test_email_draft_service_converts_model_exception() -> None:
    service = EmailDraftService(model=FakeModel(error=RuntimeError("model down")))

    with pytest.raises(EmailDraftGenerationError, match="model call failed"):
        service.generate(make_input())


def test_email_draft_service_regenerates_once_after_quality_failure() -> None:
    model = FakeModel(
        replies=[
            ModelReply(content="not valid json", model="fake-email-model"),
            ModelReply(
                content=json.dumps(
                    {
                        "subject": "Academic exchange on CRISPR imaging",
                        "body": "CRISPR imaging can help examine genome dynamics.",
                    }
                ),
                model="fake-email-model",
            ),
        ]
    )

    draft = EmailDraftService(model=model).generate(make_input())

    assert len(model.calls) == 2
    assert draft.draft_status == "review_pending"
    assert draft.evidence["quality_report"]["status"] == "warning"
    assert "invalid_json" in model.calls[1]["messages"][-1]["content"]


def test_email_draft_service_stops_after_second_quality_failure() -> None:
    model = FakeModel(
        replies=[
            ModelReply(content="not valid json", model="fake-email-model"),
            ModelReply(content="still not json", model="fake-email-model"),
        ]
    )

    draft = EmailDraftService(model=model).generate(make_input())

    assert len(model.calls) == 2
    assert draft.draft_status == "quality_failed"
    assert draft.can_send is False
    assert draft.evidence["quality_report"]["status"] == "fail"
    assert "quality_failed" in draft.warnings


def test_parse_email_draft_model_output_supports_subject_body_text() -> None:
    subject, body = parse_email_draft_model_output(
        "Subject: Collaboration on CRISPR imaging\nBody:\nDear Dr. Qi,\nHello."
    )

    assert subject == "Collaboration on CRISPR imaging"
    assert body.startswith("Dear Dr. Qi")
