"""Helpers for PubMed email evidence and future lead generation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import re

from scholarlead_agent.pubmed_models import (
    PubMedAuthor,
    PubMedEmailEvidence,
    PubMedLead,
    PubMedPaper,
)


EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    r"(?![A-Za-z0-9._%+-])"
)
EMAIL_TOKEN_PATTERN = re.compile(r"[^\s,;()<>]+@[^\s,;()<>]+")


def extract_email_evidence_from_paper(paper: PubMedPaper) -> list[PubMedEmailEvidence]:
    """Extract email evidence from PubMed affiliation text only."""

    evidence: list[PubMedEmailEvidence] = []
    affiliation_authors = _build_affiliation_author_map(paper.authors)

    for author in paper.authors:
        for affiliation in author.affiliations:
            evidence.extend(
                _extract_evidence_from_affiliation(
                    affiliation=affiliation,
                    paper=paper,
                    matched_authors=affiliation_authors[affiliation],
                    current_author=author,
                )
            )

    if not paper.authors:
        for affiliation in paper.affiliations:
            evidence.extend(
                _extract_evidence_from_affiliation(
                    affiliation=affiliation,
                    paper=paper,
                    matched_authors=[],
                    current_author=None,
                )
            )

    deduplicated = _deduplicate_email_evidence(evidence)
    if deduplicated:
        return deduplicated

    return [
        PubMedEmailEvidence(
            email=None,
            email_status="missing",
            email_source_type="pubmed_affiliation",
            email_source_url=paper.source_url,
            matched_author_name=None,
            matched_affiliation=None,
            name_email_match_confidence="missing",
            email_reason="source_data_not_provided",
        )
    ]


def extract_valid_emails_from_text(text: str) -> list[str]:
    """Return normalized valid emails from a text block."""

    return _deduplicate_strings(match.group(1).lower() for match in EMAIL_PATTERN.finditer(text))


def is_valid_email(value: str) -> bool:
    """Return whether a value is a complete email address."""

    return EMAIL_PATTERN.fullmatch(value.strip()) is not None


def build_leads_from_papers(papers: list[PubMedPaper]) -> list[PubMedLead]:
    """Build PubMed-only candidate leads from parsed papers."""

    leads: list[PubMedLead] = []
    for paper in papers:
        leads.extend(build_leads_from_paper(paper))
    return leads


def build_leads_from_paper(paper: PubMedPaper) -> list[PubMedLead]:
    """Build candidate leads from one PubMed paper."""

    email_evidence = extract_email_evidence_from_paper(paper)
    contactable_leads = [
        _build_lead_from_email_evidence(paper, evidence)
        for evidence in email_evidence
        if evidence.email_status in {"verified_from_pubmed_affiliation", "needs_review"}
        and evidence.email is not None
        and evidence.email_status != "invalid_format"
    ]

    if contactable_leads:
        return contactable_leads

    last_author = _find_last_author(paper)
    if last_author is not None:
        return [_build_lead_from_author_without_email(paper, last_author)]

    return []


def deduplicate_pubmed_leads(leads: list[PubMedLead]) -> list[PubMedLead]:
    """Deduplicate strong PubMed lead matches and mark weak matches for review."""

    merged = _merge_strong_lead_matches(leads)
    return _mark_candidate_name_institution_matches(merged)


def get_pubmed_lead_strong_dedup_key(lead: PubMedLead) -> tuple[str, str] | None:
    """Return the strong deduplication key for a PubMed lead."""

    email = _normalize_key(lead.verified_email)
    if email and lead.email_status == "verified_from_pubmed_affiliation":
        return ("email", email)

    pmid = _normalize_key(lead.pmid)
    name = _normalize_key(lead.pi_full_name)
    if pmid and name:
        return ("pmid_author", f"{pmid}|{name}")

    return None


def _extract_evidence_from_affiliation(
    *,
    affiliation: str,
    paper: PubMedPaper,
    matched_authors: list[PubMedAuthor],
    current_author: PubMedAuthor | None,
) -> list[PubMedEmailEvidence]:
    valid_emails = extract_valid_emails_from_text(affiliation)
    invalid_tokens = _extract_invalid_email_tokens(affiliation, valid_emails)
    evidence: list[PubMedEmailEvidence] = []

    for email in valid_emails:
        matched_author_name, confidence = _match_author_for_affiliation(
            matched_authors=matched_authors,
            current_author=current_author,
        )
        evidence.append(
            PubMedEmailEvidence(
                email=email,
                email_status=(
                    "verified_from_pubmed_affiliation"
                    if confidence in {"high", "medium"}
                    else "needs_review"
                ),
                email_source_type="pubmed_affiliation",
                email_source_url=paper.source_url,
                matched_author_name=matched_author_name,
                matched_affiliation=affiliation,
                name_email_match_confidence=confidence,
            )
        )

    for token in invalid_tokens:
        evidence.append(
            PubMedEmailEvidence(
                email=token,
                email_status="invalid_format",
                email_source_type="pubmed_affiliation",
                email_source_url=paper.source_url,
                matched_author_name=current_author.full_name if current_author else None,
                matched_affiliation=affiliation,
                name_email_match_confidence="invalid_format",
                email_reason="invalid_email_format",
            )
        )

    return evidence


def _merge_strong_lead_matches(leads: list[PubMedLead]) -> list[PubMedLead]:
    seen: dict[tuple[str, str], int] = {}
    results: list[PubMedLead] = []

    for lead in leads:
        key = get_pubmed_lead_strong_dedup_key(lead)
        if key is None:
            results.append(lead)
            continue

        if key not in seen:
            seen[key] = len(results)
            results.append(lead)
            continue

        existing_index = seen[key]
        existing = results[existing_index]
        results[existing_index] = _merge_duplicate_leads(existing, lead, key=key)

    return results


def _merge_duplicate_leads(
    existing: PubMedLead,
    duplicate: PubMedLead,
    *,
    key: tuple[str, str],
) -> PubMedLead:
    merge_reason = "email_match" if key[0] == "email" else "same_pmid_author"
    return replace(
        existing,
        source_links=_merge_source_links(existing.source_links, duplicate.source_links),
        manual_review_required=(
            existing.manual_review_required or duplicate.manual_review_required
        ),
        merge_status="confirmed",
        merge_reason=merge_reason,
        notes=_append_note(existing.notes, f"Merged duplicate lead by {merge_reason}."),
    )


def _mark_candidate_name_institution_matches(
    leads: list[PubMedLead],
) -> list[PubMedLead]:
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    results = list(leads)

    for index, lead in enumerate(results):
        name = _normalize_key(lead.pi_full_name)
        institution = _normalize_key(lead.institution)
        if not name or not institution:
            continue
        groups[(name, institution)].append(index)

    for indexes in groups.values():
        if len(indexes) <= 1:
            continue
        for index in indexes:
            lead = results[index]
            if lead.merge_status == "confirmed":
                continue
            results[index] = replace(
                lead,
                manual_review_required=True,
                merge_status="candidate",
                merge_reason="same_name_institution",
                notes=_append_note(
                    lead.notes,
                    "Possible duplicate: same name and institution; manual review required.",
                ),
            )

    return results


def _merge_source_links(first: list[str], second: list[str]) -> list[str]:
    return _deduplicate_strings([*first, *second])


def _append_note(existing_note: str, new_note: str) -> str:
    if not existing_note:
        return new_note
    if new_note in existing_note:
        return existing_note
    return f"{existing_note} {new_note}"


def _normalize_key(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.lower().split())


def _build_lead_from_email_evidence(
    paper: PubMedPaper,
    evidence: PubMedEmailEvidence,
) -> PubMedLead:
    author = _find_author_by_name(paper.authors, evidence.matched_author_name)
    author_name = evidence.matched_author_name or "unknown"
    manual_review_required = evidence.name_email_match_confidence != "high"

    return PubMedLead(
        lead_id=_build_lead_id(
            pmid=paper.pmid,
            author_name=author_name,
            email=evidence.email,
        ),
        pi_full_name=author_name,
        verified_email=evidence.email,
        email_status=evidence.email_status,
        email_source_url=evidence.email_source_url,
        email_source_type=evidence.email_source_type,
        name_email_match_confidence=evidence.name_email_match_confidence,
        institution=_select_institution(
            author.affiliations if author is not None else [evidence.matched_affiliation]
        ),
        country="unknown",
        country_confidence="pending",
        recent_publication_title=paper.title,
        abstract=paper.abstract,
        journal=paper.journal,
        publication_year=paper.publication_year,
        pmid=paper.pmid,
        doi=paper.doi,
        author_role=_determine_author_role(author, has_email=True),
        source_links=[paper.source_url] if paper.source_url else [],
        data_quality=(
            "email_evidence_available"
            if not manual_review_required
            else "email_evidence_needs_review"
        ),
        manual_review_required=manual_review_required,
        notes=(
            "Email found in PubMed affiliation."
            if not manual_review_required
            else "Email found in PubMed affiliation, but author match needs review."
        ),
    )


def _build_lead_from_author_without_email(
    paper: PubMedPaper,
    author: PubMedAuthor,
) -> PubMedLead:
    return PubMedLead(
        lead_id=_build_lead_id(
            pmid=paper.pmid,
            author_name=author.full_name,
            email=None,
        ),
        pi_full_name=author.full_name,
        verified_email=None,
        email_status="missing",
        email_source_url=paper.source_url,
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="missing",
        institution=_select_institution(author.affiliations),
        country="unknown",
        country_confidence="pending",
        recent_publication_title=paper.title,
        abstract=paper.abstract,
        journal=paper.journal,
        publication_year=paper.publication_year,
        pmid=paper.pmid,
        doi=paper.doi,
        author_role="candidate_pi_last_author",
        source_links=[paper.source_url] if paper.source_url else [],
        data_quality="missing_email_candidate",
        manual_review_required=True,
        notes="No email found in PubMed affiliation; last author retained as PI candidate, not confirmed PI.",
    )


def _find_last_author(paper: PubMedPaper) -> PubMedAuthor | None:
    for author in paper.authors:
        if author.is_last_author:
            return author
    return paper.authors[-1] if paper.authors else None


def _find_author_by_name(
    authors: list[PubMedAuthor],
    author_name: str | None,
) -> PubMedAuthor | None:
    if author_name is None:
        return None
    for author in authors:
        if author.full_name == author_name:
            return author
    return None


def _determine_author_role(
    author: PubMedAuthor | None,
    *,
    has_email: bool,
) -> str:
    if author is None:
        return "email_author_needs_review" if has_email else "candidate"
    if has_email:
        return "email_author"
    if author.is_last_author:
        return "candidate_pi_last_author"
    return "candidate_author"


def _select_institution(affiliations: list[str | None]) -> str | None:
    for affiliation in affiliations:
        if affiliation:
            return affiliation
    return None


def _build_lead_id(
    *,
    pmid: str,
    author_name: str,
    email: str | None,
) -> str:
    identity = email or author_name or "unknown"
    raw_id = f"pubmed-{pmid}-{identity}"
    return re.sub(r"[^a-zA-Z0-9]+", "-", raw_id).strip("-").lower()


def _match_author_for_affiliation(
    *,
    matched_authors: list[PubMedAuthor],
    current_author: PubMedAuthor | None,
) -> tuple[str | None, str]:
    if len(matched_authors) == 1:
        return matched_authors[0].full_name, "high"
    if len(matched_authors) > 1 and current_author is not None:
        return current_author.full_name, "medium"
    return None, "needs_review"


def _build_affiliation_author_map(
    authors: list[PubMedAuthor],
) -> dict[str, list[PubMedAuthor]]:
    affiliation_authors: dict[str, list[PubMedAuthor]] = defaultdict(list)
    for author in authors:
        for affiliation in author.affiliations:
            affiliation_authors[affiliation].append(author)
    return affiliation_authors


def _extract_invalid_email_tokens(text: str, valid_emails: list[str]) -> list[str]:
    valid_email_set = set(valid_emails)
    invalid_tokens: list[str] = []

    for match in EMAIL_TOKEN_PATTERN.finditer(text):
        token = match.group(0).strip().strip(".")
        if token.lower() not in valid_email_set and not is_valid_email(token):
            invalid_tokens.append(token)

    return _deduplicate_strings(invalid_tokens)


def _deduplicate_email_evidence(
    evidence: list[PubMedEmailEvidence],
) -> list[PubMedEmailEvidence]:
    seen: set[tuple[str | None, str | None, str | None, str]] = set()
    results: list[PubMedEmailEvidence] = []

    for item in evidence:
        key = (
            item.email,
            item.matched_author_name,
            item.matched_affiliation,
            item.email_status,
        )
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    return results


def _deduplicate_strings(values: object) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized:
            continue
        lookup = normalized.lower()
        if lookup in seen:
            continue
        seen.add(lookup)
        results.append(normalized)

    return results
