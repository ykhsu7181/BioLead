"""Deterministic quality checks for generated Academic Cold Email drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from scholarlead_agent.ai.email_drafts import DRAFT_MODE_PAPER_ONLY, EmailDraftInput


QUALITY_STATUS_PASS = "pass"
QUALITY_STATUS_WARNING = "warning"
QUALITY_STATUS_FAIL = "fail"
EMAIL_DRAFT_QUALITY_VALIDATOR_VERSION = "email_draft_quality_v1"

FAIL_EMPTY_DRAFT = "empty_draft"
FAIL_INVALID_JSON = "invalid_json"
FAIL_MISSING_SUBJECT_OR_BODY = "missing_subject_or_body"
FAIL_UNSUPPORTED_CAPABILITY_CLAIM = "unsupported_capability_claim"
FAIL_PAPER_ONLY_CAPABILITY_CLAIM = "paper_only_contains_specific_capability_claim"
FAIL_MISSING_PAPER_GROUNDING = "completely_missing_paper_grounding"

WARNING_WORD_COUNT = "word_count_slightly_outside_target"
WARNING_GENERIC_PRAISE = "generic_praise_detected"
WARNING_COLLABORATION = "collaboration_keyword_detected"
WARNING_SALES = "sales_keyword_detected"
WARNING_PARAGRAPH_COUNT = "paragraph_count_slightly_different"

_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
_GENERIC_PRAISE = ("impressive work", "excellent work", "remarkable work")
_SALES_TERMS = ("pricing", "quotation", "quote", "purchase", "procurement", "sample")


@dataclass(frozen=True)
class EmailDraftQualityReport:
    """Structured, exportable result of one deterministic quality check."""

    status: str
    failure_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    word_count: int = 0
    paragraph_count: int = 0
    validator_version: str = EMAIL_DRAFT_QUALITY_VALIDATOR_VERSION
    checked_at: str = ""


def validate_email_draft_quality(
    evidence: EmailDraftInput,
    *,
    subject: str | None,
    body: str | None,
    strict_json_output: bool,
) -> EmailDraftQualityReport:
    """Validate one generated draft without calling a model or external service."""

    subject_text = (subject or "").strip()
    body_text = (body or "").strip()
    combined = f"{subject_text}\n{body_text}".strip()
    failures: list[str] = []
    warnings: list[str] = []

    if not combined:
        failures.append(FAIL_EMPTY_DRAFT)
    if not strict_json_output:
        failures.append(FAIL_INVALID_JSON)
    if not subject_text or not body_text:
        failures.append(FAIL_MISSING_SUBJECT_OR_BODY)

    if combined and not _has_paper_grounding(evidence, combined):
        failures.append(FAIL_MISSING_PAPER_GROUNDING)

    unsupported_claim = _unsupported_capability_claim(evidence, body_text)
    if unsupported_claim:
        failures.append(unsupported_claim)

    word_count = len(_WORD_PATTERN.findall(body_text))
    paragraph_count = _paragraph_count(body_text)
    lower_body = body_text.lower()
    if body_text and not 130 <= word_count <= 160:
        warnings.append(WARNING_WORD_COUNT)
    if any(phrase in lower_body for phrase in _GENERIC_PRAISE):
        warnings.append(WARNING_GENERIC_PRAISE)
    if "collaboration" in lower_body:
        warnings.append(WARNING_COLLABORATION)
    if any(term in lower_body for term in _SALES_TERMS):
        warnings.append(WARNING_SALES)
    if body_text and paragraph_count != 3:
        warnings.append(WARNING_PARAGRAPH_COUNT)

    status = (
        QUALITY_STATUS_FAIL
        if failures
        else QUALITY_STATUS_WARNING
        if warnings
        else QUALITY_STATUS_PASS
    )
    return EmailDraftQualityReport(
        status=status,
        failure_reasons=failures,
        warnings=warnings,
        word_count=word_count,
        paragraph_count=paragraph_count,
        checked_at=datetime.now().isoformat(timespec="seconds"),
    )


def email_draft_quality_to_dict(report: EmailDraftQualityReport) -> dict[str, Any]:
    """Convert a quality report to JSON-safe audit data."""

    return {
        "status": report.status,
        "failure_reasons": list(report.failure_reasons),
        "warnings": list(report.warnings),
        "word_count": report.word_count,
        "paragraph_count": report.paragraph_count,
        "validator_version": report.validator_version,
        "checked_at": report.checked_at,
    }


def _has_paper_grounding(evidence: EmailDraftInput, content: str) -> bool:
    paper_text = " ".join(
        value
        for value in (
            evidence.recent_publication_title,
            evidence.abstract or "",
            " ".join(evidence.matched_keywords),
            evidence.paper_evidence_summary or "",
            evidence.research_direction or "",
        )
        if value
    )
    paper_terms = {
        term.lower()
        for term in _WORD_PATTERN.findall(paper_text)
        if len(term) >= 5 and term.lower() not in {"study", "research", "recent"}
    }
    content_terms = {term.lower() for term in _WORD_PATTERN.findall(content)}
    return bool(paper_terms & content_terms)


def _unsupported_capability_claim(evidence: EmailDraftInput, body: str) -> str | None:
    lower_body = body.lower()
    if evidence.draft_mode == DRAFT_MODE_PAPER_ONLY:
        if _contains_internal_capability_phrase(evidence, lower_body):
            return FAIL_PAPER_ONLY_CAPABILITY_CLAIM
        return None

    allowed_phrases = {
        value.lower().strip()
        for item in evidence.candidate_capabilities
        for value in (item.capability_name, *item.matched_terms)
        if value.strip()
    }
    internal_phrases = _internal_capability_phrases(evidence)
    if any(
        phrase in lower_body and phrase not in allowed_phrases
        for phrase in internal_phrases
    ):
        return FAIL_UNSUPPORTED_CAPABILITY_CLAIM
    return None


def _contains_internal_capability_phrase(evidence: EmailDraftInput, body: str) -> bool:
    phrases = _internal_capability_phrases(evidence)
    for sentence in re.split(r"[.!?\n]+", body):
        lower_sentence = sentence.lower()
        is_sender_claim = any(
            marker in lower_sentence
            for marker in ("we ", "our ", "i lead", "provide", "support", "service")
        )
        if is_sender_claim and any(phrase in lower_sentence for phrase in phrases):
            return True
    return False


def _internal_capability_phrases(evidence: EmailDraftInput) -> set[str]:
    values = (
        evidence.target_service_type,
        evidence.matched_service_name,
    )
    return {value.lower().strip() for value in values if value and value.strip()}


def _paragraph_count(body: str) -> int:
    return len([part for part in re.split(r"\n\s*\n", body.strip()) if part.strip()])
