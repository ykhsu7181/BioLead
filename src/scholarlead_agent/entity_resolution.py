"""Conservative entity resolution helpers for Stage 21E."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.unified_converters import evidence_from_pubmed_lead
from scholarlead_agent.unified_models import (
    EvidenceRecord,
    UnifiedContact,
    UnifiedOrganization,
    UnifiedResearcher,
)


@dataclass(frozen=True)
class ResearcherMatchReview:
    """A weak researcher match that must not be auto-merged."""

    left_researcher_id: str
    right_researcher_id: str
    match_status: str
    reason: str
    evidence_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert the review record to a serializable dictionary."""

        return {
            "left_researcher_id": self.left_researcher_id,
            "right_researcher_id": self.right_researcher_id,
            "match_status": self.match_status,
            "reason": self.reason,
            "evidence_fields": list(self.evidence_fields),
        }


@dataclass(frozen=True)
class EntityResolutionResult:
    """Structured result for the Stage 21E entity resolution draft."""

    researchers: list[UnifiedResearcher]
    organizations: list[UnifiedOrganization]
    contacts: list[UnifiedContact]
    evidence_records: list[EvidenceRecord]
    probable_matches: list[ResearcherMatchReview]
    manual_review_records: list[ResearcherMatchReview]

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to serializable dictionaries."""

        return {
            "researchers": [researcher.to_dict() for researcher in self.researchers],
            "organizations": [
                organization.to_dict() for organization in self.organizations
            ],
            "contacts": [contact.to_dict() for contact in self.contacts],
            "evidence_records": [
                evidence.to_dict() for evidence in self.evidence_records
            ],
            "probable_matches": [
                match.to_dict() for match in self.probable_matches
            ],
            "manual_review_records": [
                match.to_dict() for match in self.manual_review_records
            ],
        }


def resolve_pubmed_leads_to_entities(
    leads: list[PubMedLead],
    *,
    retrieved_at: str | None = None,
) -> EntityResolutionResult:
    """Resolve PubMed leads into conservative researcher/org/contact entities."""

    resolved_at = retrieved_at or _now_iso()
    researchers = _build_researchers(leads, retrieved_at=resolved_at)
    organizations = _build_organizations(leads, retrieved_at=resolved_at)
    contacts = _build_contacts(leads, retrieved_at=resolved_at)
    probable_matches = detect_probable_researcher_matches(researchers)
    manual_review_records = _detect_manual_review_records(researchers)
    evidence = _collect_entity_evidence(researchers, organizations, contacts)

    return EntityResolutionResult(
        researchers=researchers,
        organizations=organizations,
        contacts=contacts,
        evidence_records=evidence,
        probable_matches=probable_matches,
        manual_review_records=manual_review_records,
    )


def detect_probable_researcher_matches(
    researchers: list[UnifiedResearcher],
) -> list[ResearcherMatchReview]:
    """Find weak researcher matches without merging them."""

    groups: dict[str, list[UnifiedResearcher]] = defaultdict(list)
    for researcher in researchers:
        name_key = _normalize_key(researcher.full_name)
        if name_key:
            groups[name_key].append(researcher)

    matches: list[ResearcherMatchReview] = []
    for group in groups.values():
        if len(group) <= 1:
            continue
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                shared_org = _has_shared_value(left.organizations, right.organizations)
                reason = (
                    "same_name_institution_weak_signal"
                    if shared_org
                    else "same_name_without_strong_identifier"
                )
                fields = ["full_name", "institution"] if shared_org else ["full_name"]
                matches.append(
                    ResearcherMatchReview(
                        left_researcher_id=left.unified_id,
                        right_researcher_id=right.unified_id,
                        match_status="probable_match",
                        reason=reason,
                        evidence_fields=fields,
                    )
                )
    return matches


def _build_researchers(
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
) -> list[UnifiedResearcher]:
    groups: dict[tuple[str, str], list[PubMedLead]] = defaultdict(list)
    for lead in leads:
        email = _normalize_email(lead.verified_email)
        if email and lead.email_status != "missing":
            groups[("email", email)].append(lead)
            continue
        groups[("lead", lead.lead_id)].append(lead)

    researchers: list[UnifiedResearcher] = []
    for key, group in groups.items():
        researchers.append(
            _build_researcher_from_group(key, group, retrieved_at=retrieved_at)
        )
    return researchers


def _build_researcher_from_group(
    key: tuple[str, str],
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
) -> UnifiedResearcher:
    names = _unique_strings([lead.pi_full_name for lead in leads])
    emails = _unique_strings(
        [_normalize_email(lead.verified_email) for lead in leads if lead.verified_email]
    )
    organizations = _unique_strings([lead.institution for lead in leads])
    countries = _unique_strings(
        [lead.country for lead in leads if lead.country and lead.country != "unknown"]
    )
    source_lead_ids = [lead.lead_id for lead in leads]
    related_paper_ids = _unique_strings([lead.pmid for lead in leads])
    source_url = _first_source_url(leads)
    conflict = len({_normalize_key(name) for name in names}) > 1 or len(countries) > 1

    if conflict:
        merge_status = "manual_review_required"
        merge_reason = "same_email_conflicting_identity_fields"
        match_confidence = "conflict"
    elif key[0] == "email" and len(leads) > 1:
        merge_status = "merged"
        merge_reason = "verified_email_match"
        match_confidence = "high"
    elif key[0] == "email":
        merge_status = "distinct"
        merge_reason = "single_verified_email_lead"
        match_confidence = "high"
    else:
        merge_status = "distinct"
        merge_reason = "no_strong_identifier"
        match_confidence = "low"

    evidence = _researcher_evidence_from_leads(
        leads,
        retrieved_at=retrieved_at,
        merge_status=merge_status,
        merge_reason=merge_reason,
    )

    return UnifiedResearcher(
        unified_id=_build_researcher_id(key),
        full_name=names[0] if names else "unknown",
        emails=emails,
        organizations=organizations,
        country=countries[0] if len(countries) == 1 else None,
        source_ids={"pubmed_lead_ids": "|".join(source_lead_ids)},
        source_lead_ids=source_lead_ids,
        related_paper_ids=related_paper_ids,
        funding_ids=[],
        merge_status=merge_status,
        merge_reason=merge_reason,
        match_confidence=match_confidence,
        evidence_records=evidence,
    )


def _build_organizations(
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
) -> list[UnifiedOrganization]:
    groups: dict[tuple[str, str], list[PubMedLead]] = defaultdict(list)
    for lead in leads:
        name = _clean_text(lead.institution)
        if not name:
            continue
        country = lead.country if lead.country and lead.country != "unknown" else ""
        groups[(_normalize_key(name), _normalize_key(country))].append(lead)

    organizations: list[UnifiedOrganization] = []
    for (name_key, country_key), group in groups.items():
        names = _unique_strings([lead.institution for lead in group])
        countries = _unique_strings(
            [lead.country for lead in group if lead.country and lead.country != "unknown"]
        )
        source_record_ids = [lead.lead_id for lead in group]
        merge_status = "merged" if len(group) > 1 else "distinct"
        merge_reason = (
            "same_normalized_name_country"
            if len(group) > 1
            else "single_source_organization"
        )
        organization_id = f"organization-{_slug(name_key)}"
        if country_key:
            organization_id = f"{organization_id}-{_slug(country_key)}"
        evidence = _organization_evidence_from_leads(
            group,
            retrieved_at=retrieved_at,
            merge_status=merge_status,
            merge_reason=merge_reason,
        )
        organizations.append(
            UnifiedOrganization(
                unified_id=organization_id,
                name=names[0],
                country=countries[0] if len(countries) == 1 else None,
                source_ids={"pubmed_lead_ids": "|".join(source_record_ids)},
                aliases=names[1:],
                source_record_ids=source_record_ids,
                merge_status=merge_status,
                merge_reason=merge_reason,
                evidence_records=evidence,
            )
        )
    return organizations


def _build_contacts(
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
) -> list[UnifiedContact]:
    contacts: dict[str, UnifiedContact] = {}
    for lead in leads:
        email = _normalize_email(lead.verified_email)
        if not email:
            continue
        evidence = _contact_evidence_from_lead(lead, email, retrieved_at=retrieved_at)
        contact_id = f"contact-email-{_slug(email)}"
        if contact_id in contacts:
            continue
        contacts[contact_id] = UnifiedContact(
            unified_id=contact_id,
            contact_type="email",
            value=email,
            status=lead.email_status,
            source_url=lead.email_source_url,
            evidence_records=evidence,
        )
    return list(contacts.values())


def _detect_manual_review_records(
    researchers: list[UnifiedResearcher],
) -> list[ResearcherMatchReview]:
    reviews: list[ResearcherMatchReview] = []
    for researcher in researchers:
        if researcher.merge_status != "manual_review_required":
            continue
        reviews.append(
            ResearcherMatchReview(
                left_researcher_id=researcher.unified_id,
                right_researcher_id=researcher.unified_id,
                match_status="manual_review_required",
                reason=researcher.merge_reason or "identity_conflict",
                evidence_fields=["verified_email", "full_name", "country"],
            )
        )
    return reviews


def _researcher_evidence_from_leads(
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
    merge_status: str,
    merge_reason: str,
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for lead in leads:
        records.extend(evidence_from_pubmed_lead(lead, retrieved_at=retrieved_at))
    source_url = _first_source_url(leads)
    source_id = "|".join(lead.lead_id for lead in leads)
    records.append(
        _entity_evidence(
            source_type="entity_resolution",
            source_id=source_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            field_name="merge_status",
            field_value=merge_status,
            confidence="high" if merge_status == "merged" else "medium",
            note=merge_reason,
        )
    )
    return records


def _organization_evidence_from_leads(
    leads: list[PubMedLead],
    *,
    retrieved_at: str,
    merge_status: str,
    merge_reason: str,
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for lead in leads:
        records.append(
            _entity_evidence(
                source_type="pubmed_lead",
                source_id=lead.lead_id,
                source_url=_first_source_url([lead]),
                retrieved_at=retrieved_at,
                field_name="institution",
                field_value=lead.institution,
                confidence="medium",
                raw_record_path=None,
                note="organization extracted from PubMed lead",
            )
        )
        records.append(
            _entity_evidence(
                source_type="pubmed_lead",
                source_id=lead.lead_id,
                source_url=_first_source_url([lead]),
                retrieved_at=retrieved_at,
                field_name="country",
                field_value=lead.country,
                confidence=lead.country_confidence,
                raw_record_path=None,
                note=lead.country_source,
            )
        )
    records.append(
        _entity_evidence(
            source_type="entity_resolution",
            source_id="|".join(lead.lead_id for lead in leads),
            source_url=_first_source_url(leads),
            retrieved_at=retrieved_at,
            field_name="merge_status",
            field_value=merge_status,
            confidence="medium",
            note=merge_reason,
        )
    )
    return [record for record in records if record.field_value]


def _contact_evidence_from_lead(
    lead: PubMedLead,
    email: str,
    *,
    retrieved_at: str,
) -> list[EvidenceRecord]:
    return [
        _entity_evidence(
            source_type="pubmed_lead",
            source_id=lead.lead_id,
            source_url=lead.email_source_url,
            retrieved_at=retrieved_at,
            field_name="verified_email",
            field_value=email,
            confidence=lead.name_email_match_confidence,
            raw_record_path=None,
            note=f"email_source_type={lead.email_source_type}",
        )
    ]


def _collect_entity_evidence(
    researchers: list[UnifiedResearcher],
    organizations: list[UnifiedOrganization],
    contacts: list[UnifiedContact],
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for researcher in researchers:
        records.extend(researcher.evidence_records)
    for organization in organizations:
        records.extend(organization.evidence_records)
    for contact in contacts:
        records.extend(contact.evidence_records)
    return records


def _entity_evidence(
    *,
    source_type: str,
    source_id: str,
    source_url: str,
    retrieved_at: str,
    field_name: str,
    field_value: Any,
    confidence: str,
    raw_record_path: str | None = None,
    note: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_name="pubmed",
        source_type=source_type,
        source_id=source_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
        field_name=field_name,
        field_value="" if field_value is None else str(field_value),
        confidence=confidence or "unknown",
        raw_record_path=raw_record_path,
        note=note,
    )


def _build_researcher_id(key: tuple[str, str]) -> str:
    if key[0] == "email":
        return f"researcher-email-{_slug(key[1])}"
    return f"researcher-lead-{_slug(key[1])}"


def _first_source_url(leads: list[PubMedLead]) -> str:
    for lead in leads:
        for link in lead.source_links:
            if link.strip():
                return link.strip()
        if lead.email_source_url:
            return lead.email_source_url
    return ""


def _normalize_email(value: str | None) -> str:
    return value.strip().lower() if value else ""


def _clean_text(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


def _normalize_key(value: str | None) -> str:
    return _clean_text(value).lower()


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(cleaned)
    return results


def _has_shared_value(first: list[str], second: list[str]) -> bool:
    first_values = {_normalize_key(value) for value in first if value}
    second_values = {_normalize_key(value) for value in second if value}
    return bool(first_values & second_values)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
