"""Prompt and data helpers for personalized English email drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any

from scholarlead_agent.pubmed_models import PubMedLead


DRAFT_STATUS_REVIEW_PENDING = "review_pending"
EMAIL_DRAFT_LANGUAGE = "en"


@dataclass(frozen=True)
class EmailDraftInput:
    """Evidence package used to generate one outreach email draft."""

    lead_id: str
    pi_full_name: str
    recent_publication_title: str
    source_url: str
    target_service_type: str
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


EMAIL_DRAFT_SYSTEM_PROMPT = """You write personalized professional English outreach email drafts for ScholarLead Agent.

Rules:
- Use only the evidence provided by the user message.
- Do not invent funding, grant status, experiment results, customer needs, affiliations, emails, or source links.
- Do not say the candidate PI / corresponding author is absolutely confirmed.
- Do not claim any email has been sent or will be sent automatically.
- The tone must be professional, concise, and restrained.
- The email must mention the recent publication evidence in a personalized way.
- Return valid JSON only with exactly two string keys: subject and body.
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
        "target_service_type": value.target_service_type,
    }
    for field_name, field_value in required_text.items():
        if not _clean_text(field_value):
            raise ValueError(f"{field_name} cannot be empty")

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
        )
    )


def build_email_draft_messages(evidence: EmailDraftInput) -> list[dict[str, str]]:
    """Build model messages for one email draft request."""

    normalized = validate_email_draft_input(evidence)
    user_prompt = (
        "Generate one English outreach email draft from this evidence only.\n"
        "Do not include any funding claim unless funding evidence is explicitly provided; "
        "no funding evidence is provided in this task.\n\n"
        f"{json.dumps(build_email_draft_evidence(normalized), ensure_ascii=False, indent=2)}"
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
        },
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


def build_email_draft(
    *,
    evidence: EmailDraftInput,
    subject: str,
    body: str,
    model_name: str | None,
    generated_at: str | None = None,
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

    return EmailDraft(
        lead_id=normalized.lead_id,
        subject=subject.strip(),
        body=body.strip(),
        language=EMAIL_DRAFT_LANGUAGE,
        draft_status=DRAFT_STATUS_REVIEW_PENDING,
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
        evidence=build_email_draft_evidence(normalized),
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
