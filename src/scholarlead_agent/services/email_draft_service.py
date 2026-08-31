"""Service layer for AI-generated email drafts."""

from __future__ import annotations

from dataclasses import dataclass

from scholarlead_agent.adapters.openai_compatible_chat import OpenAICompatibleChatAdapter
from scholarlead_agent.capability_matching import (
    CAPABILITY_MATCH_STATUS_NO_MATCH,
    capability_match_input_from_lead,
    match_sender_capabilities,
)
from scholarlead_agent.ai.email_drafts import (
    EmailDraft,
    EmailDraftInput,
    build_email_draft,
    build_email_draft_messages,
    parse_email_draft_model_json,
    parse_email_draft_model_output,
    validate_email_draft_input,
)
from scholarlead_agent.ai.email_draft_quality import (
    QUALITY_STATUS_FAIL,
    email_draft_quality_to_dict,
    validate_email_draft_quality,
)
from scholarlead_agent.ai.model_config import FEATURE_EMAIL_DRAFT
from scholarlead_agent.ai.usage import UsageTrackingModelClient
from scholarlead_agent.agent.model import ModelClient
from scholarlead_agent.config import load_config
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_profile import SenderProfile, load_sender_profile
from scholarlead_agent.sender_capabilities import (
    SenderCapabilityCatalog,
    load_sender_capability_catalog,
)
from scholarlead_agent.service_catalog import (
    CompanyService,
    CompanyServiceCatalog,
    load_company_service_catalog,
)
from scholarlead_agent.service_matching import (
    ServiceMatchResult,
    match_company_service,
    service_match_input_from_lead,
)


class EmailDraftGenerationError(RuntimeError):
    """Raised when a model cannot generate a usable email draft."""


@dataclass
class EmailDraftService:
    """Generate structured email drafts from lead evidence."""

    model: ModelClient | None = None

    def generate(self, evidence: EmailDraftInput) -> EmailDraft:
        """Generate one English email draft for human review."""

        normalized = validate_email_draft_input(evidence)
        model = self.model or _build_default_email_draft_model(normalized.lead_id)
        messages = build_email_draft_messages(normalized)
        last_subject = ""
        last_body = ""
        last_model_name: str | None = None
        last_report = None

        for attempt in range(2):
            try:
                reply = model.complete(messages=messages, tools=[])
            except Exception as error:
                raise EmailDraftGenerationError(f"model call failed: {error}") from error

            last_model_name = reply.model
            last_subject, last_body, strict_json_output = _parse_model_reply(reply.content)
            last_report = validate_email_draft_quality(
                normalized,
                subject=last_subject,
                body=last_body,
                strict_json_output=strict_json_output,
            )
            if last_report.status != QUALITY_STATUS_FAIL:
                return build_email_draft(
                    evidence=normalized,
                    subject=last_subject,
                    body=last_body,
                    model_name=last_model_name,
                    quality_report=email_draft_quality_to_dict(last_report),
                    additional_warnings=last_report.warnings,
                )

            if attempt == 0:
                messages = _build_regeneration_messages(
                    messages,
                    last_report.failure_reasons,
                )

        assert last_report is not None
        return build_email_draft(
            evidence=normalized,
            subject=last_subject,
            body=last_body,
            model_name=last_model_name,
            draft_status="quality_failed",
            quality_report=email_draft_quality_to_dict(last_report),
            additional_warnings=["quality_failed", *last_report.failure_reasons],
        )

    def generate_for_lead(
        self,
        lead: PubMedLead,
        *,
        catalog: CompanyServiceCatalog | None = None,
        sender_profile: SenderProfile | None = None,
        capability_catalog: SenderCapabilityCatalog | None = None,
    ) -> EmailDraft:
        """Match a company service, inject sender profile, and generate a draft."""

        evidence = build_auto_email_draft_input_from_lead(
            lead,
            catalog=catalog,
            sender_profile=sender_profile,
            capability_catalog=capability_catalog,
        )
        return self.generate(evidence)


def build_auto_email_draft_input_from_lead(
    lead: PubMedLead,
    *,
    catalog: CompanyServiceCatalog | None = None,
    sender_profile: SenderProfile | None = None,
    capability_catalog: SenderCapabilityCatalog | None = None,
) -> EmailDraftInput:
    """Build draft evidence from service and capability matches independently."""

    active_catalog = catalog or load_company_service_catalog()
    active_profile = sender_profile or load_sender_profile()
    active_capability_catalog = capability_catalog or load_sender_capability_catalog()
    service_match = match_company_service(
        service_match_input_from_lead(lead),
        active_catalog,
    )
    capability_match = match_sender_capabilities(
        capability_match_input_from_lead(lead),
        active_capability_catalog,
    )
    matched_service = (
        _find_service(active_catalog, service_match.service_id)
        if service_match.service_id
        else None
    )
    service_context = (
        _build_service_context(matched_service, service_match)
        if matched_service is not None
        else None
    )

    return validate_email_draft_input(
        EmailDraftInput(
            lead_id=lead.lead_id,
            pi_full_name=lead.pi_full_name,
            recent_publication_title=lead.recent_publication_title,
            abstract=lead.abstract,
            institution=lead.institution,
            country=lead.country,
            verified_email=lead.verified_email,
            email_status=lead.email_status,
            pmid=lead.pmid,
            doi=lead.doi,
            source_url=lead.source_links[0] if lead.source_links else "",
            matched_keywords=lead.matched_keywords,
            target_service_type=service_match.service_name or "",
            sender_name=active_profile.sender_name,
            sender_title=active_profile.sender_title,
            organization_name=active_profile.sender_organization,
            service_context=service_context,
            matched_service_id=service_match.service_id,
            matched_service_name=service_match.service_name,
            service_match_score=service_match.match_score,
            service_match_reason=service_match.match_reason,
            service_matched_terms=service_match.matched_terms,
            service_match_status=service_match.status,
            service_catalog_version=service_match.catalog_version,
            service_matcher_version=service_match.matcher_version,
            sender_profile_version=active_profile.profile_version,
            sender_email=active_profile.sender_email,
            sender_signature=active_profile.signature,
            sender_intro_style=active_profile.sender_intro_style,
            capability_match_id=capability_match.capability_match_id,
            candidate_capabilities=capability_match.items,
            capability_match_status=capability_match.status,
            capability_profile_version=capability_match.profile_version,
            capability_matcher_version=capability_match.matcher_version,
            paper_evidence_source_refs=[
                lead.source_links[0] if lead.source_links else "",
            ],
            draft_mode=(
                "paper_only"
                if capability_match.status == CAPABILITY_MATCH_STATUS_NO_MATCH
                else "capability_grounded"
            ),
        )
    )


def _find_service(
    catalog: CompanyServiceCatalog,
    service_id: str,
) -> CompanyService | None:
    for service in catalog.services:
        if service.service_id == service_id:
            return service
    return None


def _build_service_context(
    service: CompanyService | None,
    match_result: ServiceMatchResult,
) -> str:
    parts: list[str] = []
    if service is not None:
        for value in (
            service.description,
            service.company_capability,
            service.selling_points,
            service.email_talking_points,
        ):
            cleaned = value.strip()
            if cleaned:
                parts.append(cleaned)
    parts.append(f"Service match reason: {match_result.match_reason}")
    parts.append(f"Matched terms: {', '.join(match_result.matched_terms)}")
    return "\n".join(parts)


def _build_default_email_draft_model(lead_id: str | None = None) -> ModelClient:
    config = load_config()
    adapter = OpenAICompatibleChatAdapter(
        config=config,
        feature_module=FEATURE_EMAIL_DRAFT,
    )
    return UsageTrackingModelClient(
        inner=adapter,
        feature_module=FEATURE_EMAIL_DRAFT,
        config=config,
        lead_id=lead_id,
    )


def _parse_model_reply(content: str) -> tuple[str, str, bool]:
    """Keep malformed output for audit, while recording its strict JSON failure."""

    try:
        subject, body = parse_email_draft_model_json(content)
        return subject, body, True
    except ValueError:
        if not content or not content.strip():
            return "", "", False
        subject, body = parse_email_draft_model_output(content)
        return subject, body, False


def _build_regeneration_messages(
    messages: list[dict[str, str]],
    failure_reasons: list[str],
) -> list[dict[str, str]]:
    """Request one correction without adding new paper or capability evidence."""

    return [
        *messages,
        {
            "role": "user",
            "content": (
                "Regenerate once using exactly the same evidence. Correct these "
                f"quality failures: {', '.join(failure_reasons)}. Return strict JSON only."
            ),
        },
    ]
