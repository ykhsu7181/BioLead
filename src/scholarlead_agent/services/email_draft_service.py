"""Service layer for AI-generated email drafts."""

from __future__ import annotations

from dataclasses import dataclass

from scholarlead_agent.adapters.openai_compatible_chat import OpenAICompatibleChatAdapter
from scholarlead_agent.ai.email_drafts import (
    EmailDraft,
    EmailDraftInput,
    build_email_draft,
    build_email_draft_messages,
    parse_email_draft_model_output,
    validate_email_draft_input,
)
from scholarlead_agent.ai.model_config import FEATURE_EMAIL_DRAFT
from scholarlead_agent.ai.usage import UsageTrackingModelClient
from scholarlead_agent.agent.model import ModelClient
from scholarlead_agent.config import load_config
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_profile import SenderProfile, load_sender_profile
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

        try:
            reply = model.complete(messages=messages, tools=[])
        except Exception as error:
            raise EmailDraftGenerationError(f"model call failed: {error}") from error

        if not reply.content or not reply.content.strip():
            raise EmailDraftGenerationError("model returned no email draft content")

        try:
            subject, body = parse_email_draft_model_output(reply.content)
        except ValueError as error:
            raise EmailDraftGenerationError(str(error)) from error

        return build_email_draft(
            evidence=normalized,
            subject=subject,
            body=body,
            model_name=reply.model,
        )

    def generate_for_lead(
        self,
        lead: PubMedLead,
        *,
        catalog: CompanyServiceCatalog | None = None,
        sender_profile: SenderProfile | None = None,
    ) -> EmailDraft:
        """Match a company service, inject sender profile, and generate a draft."""

        evidence = build_auto_email_draft_input_from_lead(
            lead,
            catalog=catalog,
            sender_profile=sender_profile,
        )
        return self.generate(evidence)


def build_auto_email_draft_input_from_lead(
    lead: PubMedLead,
    *,
    catalog: CompanyServiceCatalog | None = None,
    sender_profile: SenderProfile | None = None,
) -> EmailDraftInput:
    """Build draft evidence using ServiceMatcher and fixed SenderProfile."""

    active_catalog = catalog or load_company_service_catalog()
    active_profile = sender_profile or load_sender_profile()
    match_result = match_company_service(
        service_match_input_from_lead(lead),
        active_catalog,
    )
    if not match_result.service_id or not match_result.service_name:
        raise EmailDraftGenerationError(
            f"no enabled matched service for lead {lead.lead_id}: "
            f"{match_result.status}"
        )

    matched_service = _find_service(active_catalog, match_result.service_id)
    service_context = _build_service_context(matched_service, match_result)

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
            target_service_type=match_result.service_name,
            sender_name=active_profile.sender_name,
            sender_title=active_profile.sender_title,
            organization_name=active_profile.sender_organization,
            service_context=service_context,
            matched_service_id=match_result.service_id,
            matched_service_name=match_result.service_name,
            service_match_score=match_result.match_score,
            service_match_reason=match_result.match_reason,
            service_matched_terms=match_result.matched_terms,
            service_match_status=match_result.status,
            service_catalog_version=match_result.catalog_version,
            service_matcher_version=match_result.matcher_version,
            sender_profile_version=active_profile.profile_version,
            sender_email=active_profile.sender_email,
            sender_signature=active_profile.signature,
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
