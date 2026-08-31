"""Prompt and data helpers for personalized English email drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any

from scholarlead_agent.capability_matching import CapabilityMatchItem
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_profile import (
    SENDER_INTRO_STYLE_I_LEAD,
    SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE,
)


DRAFT_STATUS_REVIEW_PENDING = "review_pending"
EMAIL_DRAFT_LANGUAGE = "en"
DRAFT_MODE_LEGACY_SERVICE_BASED = "legacy_service_based"
DRAFT_MODE_CAPABILITY_GROUNDED = "capability_grounded"
DRAFT_MODE_PAPER_ONLY = "paper_only"
EMAIL_DRAFT_PROMPT_VERSION_V2 = "academic_cold_email_v2"


@dataclass(frozen=True)
class EmailDraftInput:
    """Evidence package used to generate one outreach email draft."""

    lead_id: str
    pi_full_name: str
    recent_publication_title: str
    source_url: str
    target_service_type: str = ""
    abstract: str | None = None
    institution: str | None = None
    country: str | None = None
    verified_email: str | None = None
    email_status: str | None = None
    pmid: str | None = None
    doi: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    sender_name: str | None = None
    sender_title: str | None = None
    organization_name: str | None = None
    service_context: str | None = None
    matched_service_id: str | None = None
    matched_service_name: str | None = None
    service_match_score: float | None = None
    service_match_reason: str | None = None
    service_matched_terms: list[str] = field(default_factory=list)
    service_match_status: str | None = None
    service_catalog_version: str | None = None
    service_matcher_version: str | None = None
    sender_profile_version: str | None = None
    sender_email: str | None = None
    sender_signature: str | None = None
    sender_intro_style: str | None = None
    capability_match_id: str | None = None
    candidate_capabilities: list[CapabilityMatchItem] = field(default_factory=list)
    capability_match_status: str | None = None
    capability_profile_version: str | None = None
    capability_matcher_version: str | None = None
    paper_evidence_summary: str | None = None
    paper_evidence_source_refs: list[str] = field(default_factory=list)
    research_direction: str | None = None
    draft_mode: str | None = None
    email_prompt_version: str | None = None


@dataclass(frozen=True)
class EmailDraft:
    """Structured result for a generated, human-review-only email draft."""

    lead_id: str
    subject: str
    body: str
    language: str
    draft_status: str
    generated_at: str
    model_name: str
    source_paper_title: str
    source_pmid: str | None
    doi: str | None
    source_url: str
    target_service_type: str
    human_reviewer: str | None = None
    reviewed_at: str | None = None
    recipient_name: str | None = None
    verified_email: str | None = None
    email_status: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    can_send: bool = False


EMAIL_DRAFT_SYSTEM_PROMPT = """You write one restrained English Academic Cold Email draft.

Hard rules:
- Use only the evidence in the user message. Do not invent paper content, funding, experiment results, customer needs, affiliations, emails, source links, or sender capabilities.
- Do not state that the recipient is certainly a PI or corresponding author.
- Do not state that an email was sent or will be sent automatically.
- Do not use sales language, quotations, pricing, sample requests, procurement requests, meeting invitations, or project proposals.
- Return valid JSON only with exactly two non-empty string keys: subject and body.

Format rules:
- Subject: use "Academic exchange on ..." plus a specific scientific topic grounded in the paper evidence. If no specific topic is supported, use "Academic exchange on your recent research".
- Body: start with the supplied greeting, then write three concise paragraphs and finish with the supplied signature.
- Paragraph 1: make one concrete observation grounded in the paper title, abstract, keywords, or supplied metadata. Do not give generic praise alone.
- Paragraph 2: follow the supplied draft mode exactly. In capability_grounded mode, refer naturally only to supplied candidate capabilities; do not list them as products. In paper_only mode, express only the supplied general scientific interest and never claim a specific sender technique, platform, service, or capability.
- Paragraph 3: invite a low-pressure academic exchange only. Do not request a meeting or commercial action.
- Use "I lead" only when sender_intro_style is "i_lead". Otherwise use a neutral organization-representative introduction.
"""


def validate_email_draft_input(value: EmailDraftInput) -> EmailDraftInput:
    """Validate and normalize one email draft input package."""

    if not isinstance(value, EmailDraftInput):
        raise ValueError("email draft input must be an EmailDraftInput")

    required_text = {
        "lead_id": value.lead_id,
        "pi_full_name": value.pi_full_name,
        "recent_publication_title": value.recent_publication_title,
        "source_url": value.source_url,
    }
    for field_name, field_value in required_text.items():
        if not _clean_text(field_value):
            raise ValueError(f"{field_name} cannot be empty")

    candidate_capabilities = _normalize_candidate_capabilities(
        value.candidate_capabilities
    )
    capability_match_status = _clean_text(value.capability_match_status)
    if capability_match_status == "no_match" and candidate_capabilities:
        raise ValueError("no_match cannot include candidate capabilities")
    if capability_match_status in {"matched", "partial_match"} and not candidate_capabilities:
        raise ValueError(
            f"{capability_match_status} requires candidate capabilities"
        )

    sender_intro_style = _clean_text(value.sender_intro_style)
    if sender_intro_style and sender_intro_style not in {
        SENDER_INTRO_STYLE_I_LEAD,
        SENDER_INTRO_STYLE_ORGANIZATION_REPRESENTATIVE,
    }:
        raise ValueError("sender_intro_style is not supported")

    draft_mode = _clean_text(value.draft_mode) or _default_draft_mode(
        capability_match_status,
        candidate_capabilities,
    )

    return EmailDraftInput(
        lead_id=_clean_text(value.lead_id) or "",
        pi_full_name=_clean_text(value.pi_full_name) or "",
        recent_publication_title=_clean_text(value.recent_publication_title) or "",
        source_url=_clean_text(value.source_url) or "",
        target_service_type=_clean_text(value.target_service_type) or "",
        abstract=_clean_text(value.abstract),
        institution=_clean_text(value.institution),
        country=_clean_text(value.country),
        verified_email=_clean_text(value.verified_email),
        email_status=_clean_text(value.email_status),
        pmid=_clean_text(value.pmid),
        doi=_clean_text(value.doi),
        matched_keywords=[item for item in (_clean_text(k) for k in value.matched_keywords) if item],
        sender_name=_clean_text(value.sender_name),
        sender_title=_clean_text(value.sender_title),
        organization_name=_clean_text(value.organization_name),
        service_context=_clean_text(value.service_context),
        matched_service_id=_clean_text(value.matched_service_id),
        matched_service_name=_clean_text(value.matched_service_name),
        service_match_score=value.service_match_score,
        service_match_reason=_clean_text(value.service_match_reason),
        service_matched_terms=[
            item for item in (_clean_text(k) for k in value.service_matched_terms) if item
        ],
        service_match_status=_clean_text(value.service_match_status),
        service_catalog_version=_clean_text(value.service_catalog_version),
        service_matcher_version=_clean_text(value.service_matcher_version),
        sender_profile_version=_clean_text(value.sender_profile_version),
        sender_email=_clean_text(value.sender_email),
        sender_signature=_clean_text(value.sender_signature),
        sender_intro_style=sender_intro_style,
        capability_match_id=_clean_text(value.capability_match_id),
        candidate_capabilities=candidate_capabilities,
        capability_match_status=capability_match_status,
        capability_profile_version=_clean_text(value.capability_profile_version),
        capability_matcher_version=_clean_text(value.capability_matcher_version),
        paper_evidence_summary=_clean_text(value.paper_evidence_summary),
        paper_evidence_source_refs=[
            item
            for item in (_clean_text(ref) for ref in value.paper_evidence_source_refs)
            if item
        ],
        research_direction=_clean_text(value.research_direction),
        draft_mode=draft_mode,
        email_prompt_version=(
            _clean_text(value.email_prompt_version) or EMAIL_DRAFT_PROMPT_VERSION_V2
        ),
    )


def build_email_draft_input_from_lead(
    lead: PubMedLead,
    *,
    target_service_type: str | None = None,
    sender_name: str | None = None,
    sender_title: str | None = None,
    organization_name: str | None = None,
    service_context: str | None = None,
    matched_service_id: str | None = None,
    matched_service_name: str | None = None,
    service_match_score: float | None = None,
    service_match_reason: str | None = None,
    service_matched_terms: list[str] | None = None,
    service_match_status: str | None = None,
    service_catalog_version: str | None = None,
    service_matcher_version: str | None = None,
    sender_profile_version: str | None = None,
    sender_email: str | None = None,
    sender_signature: str | None = None,
    sender_intro_style: str | None = None,
    capability_match_id: str | None = None,
    candidate_capabilities: list[CapabilityMatchItem] | None = None,
    capability_match_status: str | None = None,
    capability_profile_version: str | None = None,
    capability_matcher_version: str | None = None,
    paper_evidence_summary: str | None = None,
    paper_evidence_source_refs: list[str] | None = None,
    research_direction: str | None = None,
    draft_mode: str | None = None,
    email_prompt_version: str | None = None,
) -> EmailDraftInput:
    """Build draft evidence from an existing PubMed Lead."""

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
            target_service_type=target_service_type or lead.target_service_type or "",
            sender_name=sender_name,
            sender_title=sender_title,
            organization_name=organization_name,
            service_context=service_context,
            matched_service_id=matched_service_id,
            matched_service_name=matched_service_name,
            service_match_score=service_match_score,
            service_match_reason=service_match_reason,
            service_matched_terms=service_matched_terms or [],
            service_match_status=service_match_status,
            service_catalog_version=service_catalog_version,
            service_matcher_version=service_matcher_version,
            sender_profile_version=sender_profile_version,
            sender_email=sender_email,
            sender_signature=sender_signature,
            sender_intro_style=sender_intro_style,
            capability_match_id=capability_match_id,
            candidate_capabilities=candidate_capabilities or [],
            capability_match_status=capability_match_status,
            capability_profile_version=capability_profile_version,
            capability_matcher_version=capability_matcher_version,
            paper_evidence_summary=paper_evidence_summary,
            paper_evidence_source_refs=paper_evidence_source_refs or [],
            research_direction=research_direction,
            draft_mode=draft_mode,
            email_prompt_version=email_prompt_version,
        )
    )


def build_email_draft_messages(evidence: EmailDraftInput) -> list[dict[str, str]]:
    """Build model messages for one email draft request."""

    normalized = validate_email_draft_input(evidence)
    user_prompt = (
        "Generate the email from this model-visible evidence only. "
        "no funding evidence is provided.\n\n"
        f"{json.dumps(_build_model_evidence(normalized), ensure_ascii=False, indent=2)}"
    )
    return [
        {"role": "system", "content": EMAIL_DRAFT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_email_draft_evidence(evidence: EmailDraftInput) -> dict[str, Any]:
    """Return the model-visible evidence without secrets or hidden context."""

    normalized = validate_email_draft_input(evidence)
    return {
        "lead_id": normalized.lead_id,
        "candidate_pi_name": normalized.pi_full_name,
        "institution": normalized.institution,
        "country": normalized.country,
        "verified_email": normalized.verified_email,
        "email_status": normalized.email_status,
        "recent_publication_title": normalized.recent_publication_title,
        "abstract": normalized.abstract,
        "matched_keywords": normalized.matched_keywords,
        "target_service_type": normalized.target_service_type,
        "service_context": normalized.service_context,
        "matched_service": {
            "service_id": normalized.matched_service_id,
            "service_name": normalized.matched_service_name,
            "match_score": normalized.service_match_score,
            "match_reason": normalized.service_match_reason,
            "matched_terms": normalized.service_matched_terms,
            "status": normalized.service_match_status,
            "catalog_version": normalized.service_catalog_version,
            "matcher_version": normalized.service_matcher_version,
        },
        "capability_match": {
            "capability_match_id": normalized.capability_match_id,
            "status": normalized.capability_match_status,
            "profile_version": normalized.capability_profile_version,
            "matcher_version": normalized.capability_matcher_version,
            "candidate_capabilities": [
                _capability_to_dict(capability)
                for capability in normalized.candidate_capabilities
            ],
        },
        "draft_mode": normalized.draft_mode,
        "paper_evidence_summary": normalized.paper_evidence_summary,
        "paper_evidence_source_refs": normalized.paper_evidence_source_refs,
        "research_direction": normalized.research_direction,
        "pubmed_source_url": normalized.source_url,
        "pmid": normalized.pmid,
        "doi": normalized.doi,
        "sender_name": normalized.sender_name,
        "sender_title": normalized.sender_title,
        "organization_name": normalized.organization_name,
        "sender_profile": {
            "profile_version": normalized.sender_profile_version,
            "sender_email": normalized.sender_email,
            "signature": normalized.sender_signature,
            "sender_intro_style": normalized.sender_intro_style,
        },
        "email_prompt_version": normalized.email_prompt_version,
        "funding_evidence": None,
    }


def parse_email_draft_model_output(content: str) -> tuple[str, str]:
    """Parse model output into subject and body with a conservative fallback."""

    cleaned = content.strip()
    if not cleaned:
        raise ValueError("model returned empty draft content")

    parsed = _parse_json_object(cleaned)
    if parsed:
        subject = _clean_text(parsed.get("subject"))
        body = _clean_text(parsed.get("body"))
        if subject and body:
            return subject, body

    subject = ""
    body_lines: list[str] = []
    in_body = False
    for line in cleaned.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("subject:"):
            subject = stripped.split(":", 1)[1].strip()
            continue
        if lower.startswith("body:"):
            in_body = True
            after_label = stripped.split(":", 1)[1].strip()
            if after_label:
                body_lines.append(after_label)
            continue
        if in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    if subject and body:
        return subject, body

    return "Potential academic collaboration", cleaned


def parse_email_draft_model_json(content: str) -> tuple[str, str]:
    """Parse the strict JSON response required by Academic Cold Email Prompt v2."""

    cleaned = content.strip()
    if not cleaned:
        raise ValueError("model returned empty draft content")

    parsed = _parse_json_object(cleaned)
    if not parsed or set(parsed) != {"subject", "body"}:
        raise ValueError("model output must be JSON with subject and body only")

    subject = _clean_text(parsed.get("subject"))
    body = _clean_text(parsed.get("body"))
    if not subject or not body:
        raise ValueError("model JSON subject and body cannot be empty")
    return subject, body


def build_email_draft(
    *,
    evidence: EmailDraftInput,
    subject: str,
    body: str,
    model_name: str | None,
    generated_at: str | None = None,
    draft_status: str = DRAFT_STATUS_REVIEW_PENDING,
    quality_report: dict[str, Any] | None = None,
    additional_warnings: list[str] | None = None,
) -> EmailDraft:
    """Build the final structured draft object."""

    normalized = validate_email_draft_input(evidence)
    warnings = ["human_review_required", "email_sending_not_implemented"]
    if not normalized.verified_email:
        warnings.append("missing_verified_email")
    if not normalized.abstract:
        warnings.append("missing_abstract")
    if normalized.service_match_status == "needs_review":
        warnings.append("service_match_needs_review")
    if additional_warnings:
        warnings.extend(additional_warnings)

    draft_evidence = build_email_draft_evidence(normalized)
    if quality_report is not None:
        draft_evidence["quality_report"] = quality_report

    return EmailDraft(
        lead_id=normalized.lead_id,
        subject=subject.strip(),
        body=body.strip(),
        language=EMAIL_DRAFT_LANGUAGE,
        draft_status=draft_status,
        generated_at=generated_at or datetime.now().isoformat(timespec="seconds"),
        model_name=model_name or "unknown",
        source_paper_title=normalized.recent_publication_title,
        source_pmid=normalized.pmid,
        doi=normalized.doi,
        source_url=normalized.source_url,
        target_service_type=normalized.target_service_type,
        recipient_name=normalized.pi_full_name,
        verified_email=normalized.verified_email,
        email_status=normalized.email_status,
        evidence=draft_evidence,
        warnings=warnings,
        can_send=False,
    )


def email_draft_to_dict(draft: EmailDraft) -> dict[str, Any]:
    """Convert an EmailDraft to a plain dictionary for tools and UI."""

    return {
        "lead_id": draft.lead_id,
        "subject": draft.subject,
        "body": draft.body,
        "language": draft.language,
        "draft_status": draft.draft_status,
        "generated_at": draft.generated_at,
        "model_name": draft.model_name,
        "source_paper_title": draft.source_paper_title,
        "source_pmid": draft.source_pmid,
        "doi": draft.doi,
        "source_url": draft.source_url,
        "target_service_type": draft.target_service_type,
        "human_reviewer": draft.human_reviewer,
        "reviewed_at": draft.reviewed_at,
        "recipient_name": draft.recipient_name,
        "verified_email": draft.verified_email,
        "email_status": draft.email_status,
        "evidence": draft.evidence,
        "quality_report": draft.evidence.get("quality_report"),
        "warnings": draft.warnings,
        "can_send": draft.can_send,
    }


def _parse_json_object(content: str) -> dict[str, Any] | None:
    raw = content
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None


def _normalize_candidate_capabilities(
    capabilities: list[CapabilityMatchItem],
) -> list[CapabilityMatchItem]:
    if not isinstance(capabilities, list):
        raise ValueError("candidate_capabilities must be a list")
    if any(not isinstance(item, CapabilityMatchItem) for item in capabilities):
        raise ValueError("candidate_capabilities must contain CapabilityMatchItem values")
    return list(capabilities)


def _default_draft_mode(
    capability_match_status: str | None,
    candidate_capabilities: list[CapabilityMatchItem],
) -> str:
    if capability_match_status == "no_match":
        return DRAFT_MODE_PAPER_ONLY
    if candidate_capabilities:
        return DRAFT_MODE_CAPABILITY_GROUNDED
    return DRAFT_MODE_LEGACY_SERVICE_BASED


def _capability_to_dict(capability: CapabilityMatchItem) -> dict[str, Any]:
    return {
        "capability_id": capability.capability_id,
        "capability_name": capability.capability_name,
        "match_score": capability.match_score,
        "match_reason": capability.match_reason,
        "matched_terms": list(capability.matched_terms),
        "evidence": list(capability.evidence),
    }


def _build_model_evidence(normalized: EmailDraftInput) -> dict[str, Any]:
    """Return the minimum evidence allowed to influence Prompt v2 wording."""

    data = build_email_draft_evidence(normalized)
    data["greeting"] = f"Dear {normalized.pi_full_name},"
    data["sender_intro_style"] = normalized.sender_intro_style
    data["sender_signature"] = normalized.sender_signature or _default_signature(
        normalized
    )

    if normalized.draft_mode == DRAFT_MODE_PAPER_ONLY:
        # Service matching is internal routing information, not sender evidence.
        data["target_service_type"] = None
        data["service_context"] = None
        data["matched_service"] = None
        data["capability_match"] = {
            "status": "no_match",
            "candidate_capabilities": [],
        }
        data["allowed_sender_interest"] = (
            "general academic interest in the research described by the paper"
        )
    else:
        data["allowed_sender_interest"] = None

    return data


def _default_signature(evidence: EmailDraftInput) -> str:
    lines = [
        value
        for value in (
            evidence.sender_name,
            evidence.sender_title,
            evidence.organization_name,
        )
        if value
    ]
    return "Best regards,\n" + "\n".join(lines)
