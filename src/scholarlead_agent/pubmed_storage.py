"""Storage helpers for PubMed raw and processed data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper, PubMedSearchParams


@dataclass(frozen=True)
class PubMedRawOutputPaths:
    """Raw output paths created for one PubMed collection run."""

    esearch_json: Path
    efetch_xml: Path
    request_meta_json: Path


@dataclass(frozen=True)
class PubMedProcessedOutputPaths:
    """Processed output paths created for one PubMed collection run."""

    papers_json: Path
    papers_csv: Path
    leads_json: Path
    leads_csv: Path


@dataclass(frozen=True)
class PubMedRunReportPath:
    """Run report output path created for one PubMed collection run."""

    run_report_json: Path


def build_pubmed_raw_output_paths(
    *,
    query: str,
    raw_dir: Path,
    timestamp: str | None = None,
) -> PubMedRawOutputPaths:
    """Build raw PubMed output paths for a query."""

    safe_query = _safe_filename_part(query)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_name = f"{safe_query}_{run_timestamp}"

    return PubMedRawOutputPaths(
        esearch_json=raw_dir / f"{base_name}_esearch.json",
        efetch_xml=raw_dir / f"{base_name}_efetch.xml",
        request_meta_json=raw_dir / f"{base_name}_request_meta.json",
    )


def build_pubmed_processed_output_paths(
    *,
    query: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> PubMedProcessedOutputPaths:
    """Build processed PubMed JSON/CSV output paths for a query."""

    safe_query = _safe_filename_part(query)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_name = f"{safe_query}_{run_timestamp}"

    return PubMedProcessedOutputPaths(
        papers_json=processed_dir / f"pubmed_papers_{base_name}.json",
        papers_csv=processed_dir / f"pubmed_papers_{base_name}.csv",
        leads_json=processed_dir / f"pubmed_leads_{base_name}.json",
        leads_csv=processed_dir / f"pubmed_leads_{base_name}.csv",
    )


def build_pubmed_run_report_path(
    *,
    query: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> PubMedRunReportPath:
    """Build a PubMed run report output path for a query."""

    safe_query = _safe_filename_part(query)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_name = f"{safe_query}_{run_timestamp}"
    return PubMedRunReportPath(
        run_report_json=processed_dir / f"pubmed_run_report_{base_name}.json"
    )


def save_pubmed_esearch_response(raw_response: dict[str, Any], path: Path) -> None:
    """Save the raw PubMed ESearch JSON response."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(raw_response, ensure_ascii=False, indent=2)
    _write_text_atomically(path, content)


def save_pubmed_efetch_xml(raw_xml: str, path: Path) -> None:
    """Save the raw PubMed EFetch XML response without modification."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, raw_xml)


def build_pubmed_request_meta(
    *,
    params: PubMedSearchParams,
    paths: PubMedRawOutputPaths,
    collected_at: str | None = None,
    status: str = "success",
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata describing one PubMed raw collection attempt."""

    return {
        "source": "pubmed",
        "query": params.query,
        "from_date": params.from_date,
        "to_date": params.to_date,
        "max_results": params.max_results,
        "country": params.country,
        "service_type": params.service_type,
        "collected_at": collected_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "raw_files": {
            "esearch_json": str(paths.esearch_json),
            "efetch_xml": str(paths.efetch_xml),
        },
        "errors": errors or [],
    }


def save_pubmed_request_meta(meta: dict[str, Any], path: Path) -> None:
    """Save PubMed request metadata as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(meta, ensure_ascii=False, indent=2)
    _write_text_atomically(path, content)


def save_pubmed_papers_json(papers: list[PubMedPaper], path: Path) -> None:
    """Save processed PubMed papers as stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        [_pubmed_paper_to_dict(paper) for paper in papers],
        ensure_ascii=False,
        indent=2,
    )
    _write_text_atomically(path, content)


def save_pubmed_papers_csv(papers: list[PubMedPaper], path: Path) -> None:
    """Save processed PubMed papers as Excel-friendly CSV."""

    fieldnames = [
        "Source",
        "PMID",
        "DOI",
        "Title",
        "Abstract",
        "Journal",
        "Publication_Date",
        "Publication_Year",
        "Article_Types",
        "MeSH_Terms",
        "Keywords",
        "Authors",
        "Affiliations",
        "Source_URL",
        "Raw_Record_Path",
    ]
    _write_csv(
        path,
        fieldnames=fieldnames,
        rows=[_pubmed_paper_to_csv_row(paper) for paper in papers],
    )


def save_pubmed_leads_json(leads: list[PubMedLead], path: Path) -> None:
    """Save processed PubMed leads as stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        [_pubmed_lead_to_dict(lead) for lead in leads],
        ensure_ascii=False,
        indent=2,
    )
    _write_text_atomically(path, content)


def save_pubmed_leads_csv(leads: list[PubMedLead], path: Path) -> None:
    """Save processed PubMed leads as Excel-friendly CSV."""

    fieldnames = [
        "PI_Full_Name",
        "Verified_Email",
        "Email_Status",
        "Email_Source_Type",
        "Email_Source_URL",
        "Name_Email_Match_Confidence",
        "Institution",
        "Country",
        "Country_Confidence",
        "Country_Source",
        "Raw_Affiliation",
        "Recent_Publication_Title",
        "Abstract",
        "Journal",
        "Publication_Year",
        "PMID",
        "DOI",
        "Author_Role",
        "Matched_Keywords",
        "Target_Service_Type",
        "Topic_Match_Score",
        "Publication_Recency_Score",
        "Email_Contactability_Score",
        "Lead_Score",
        "Priority",
        "Score_Explanation",
        "Data_Quality",
        "Merge_Status",
        "Merge_Reason",
        "Manual_Review_Required",
        "Funding_Activity_Score",
        "Funding_Activity_Reason",
        "Outsourcing_Tendency_Score",
        "Official_Scoring_Status",
        "Source_Links",
        "Notes",
    ]
    _write_csv(
        path,
        fieldnames=fieldnames,
        rows=[_pubmed_lead_to_csv_row(lead) for lead in leads],
    )


def save_pubmed_processed_outputs(
    *,
    papers: list[PubMedPaper],
    leads: list[PubMedLead],
    paths: PubMedProcessedOutputPaths,
) -> None:
    """Save processed PubMed papers and leads as JSON and CSV."""

    save_pubmed_papers_json(papers, paths.papers_json)
    save_pubmed_papers_csv(papers, paths.papers_csv)
    save_pubmed_leads_json(leads, paths.leads_json)
    save_pubmed_leads_csv(leads, paths.leads_csv)


def build_pubmed_run_report(
    *,
    params: PubMedSearchParams,
    task_id: str,
    pmids: list[str] | None = None,
    papers: list[PubMedPaper] | None = None,
    leads: list[PubMedLead] | None = None,
    raw_files: PubMedRawOutputPaths | dict[str, Any] | None = None,
    processed_files: PubMedProcessedOutputPaths | dict[str, Any] | None = None,
    errors: list[dict[str, Any] | str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Build an auditable PubMed run report."""

    paper_records = papers or []
    lead_records = leads or []
    normalized_pmids = _deduplicate_values(
        pmids if pmids is not None else [paper.pmid for paper in paper_records]
    )

    return {
        "task_id": task_id,
        "source": "pubmed",
        "query": params.query,
        "from_date": params.from_date,
        "to_date": params.to_date,
        "max_results": params.max_results,
        "country": params.country,
        "service_type": params.service_type,
        "pmid_count": len(normalized_pmids),
        "paper_count": len(paper_records),
        "lead_count": len(lead_records),
        "leads_with_verified_email_count": _count_verified_email_leads(
            lead_records
        ),
        "leads_needing_review_count": sum(
            1 for lead in lead_records if lead.manual_review_required
        ),
        "missing_email_count": sum(
            1
            for lead in lead_records
            if lead.email_status == "missing" or not lead.verified_email
        ),
        "unknown_country_count": sum(
            1 for lead in lead_records if lead.country == "unknown"
        ),
        "raw_files": _paths_to_dict(raw_files),
        "processed_files": _paths_to_dict(processed_files),
        "errors": _normalize_report_errors(errors),
        "started_at": started_at,
        "finished_at": finished_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "scoring_mode": "pubmed_single_source_temporary",
        "queried_sources": ["pubmed"],
        "funding_source_status": "not_connected",
        "agent_status": "not_enabled_in_first_round",
        "llm_status": "not_used_in_first_round",
    }


def save_pubmed_run_report(report: dict[str, Any], path: Path) -> None:
    """Save a PubMed run report as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    _write_text_atomically(path, content)


def _pubmed_paper_to_dict(paper: PubMedPaper) -> dict[str, Any]:
    return {
        "source": paper.source,
        "pmid": paper.pmid,
        "doi": paper.doi,
        "title": paper.title,
        "abstract": paper.abstract,
        "journal": paper.journal,
        "publication_date": paper.publication_date,
        "publication_year": paper.publication_year,
        "article_types": paper.article_types,
        "mesh_terms": paper.mesh_terms,
        "keywords": paper.keywords,
        "authors": [
            {
                "full_name": author.full_name,
                "last_name": author.last_name,
                "fore_name": author.fore_name,
                "initials": author.initials,
                "author_position": author.author_position,
                "is_last_author": author.is_last_author,
                "affiliations": author.affiliations,
            }
            for author in paper.authors
        ],
        "affiliations": paper.affiliations,
        "source_url": paper.source_url,
        "raw_record_path": paper.raw_record_path,
    }


def _pubmed_paper_to_csv_row(paper: PubMedPaper) -> dict[str, Any]:
    return {
        "Source": paper.source,
        "PMID": paper.pmid,
        "DOI": paper.doi or "",
        "Title": paper.title,
        "Abstract": paper.abstract,
        "Journal": paper.journal,
        "Publication_Date": paper.publication_date,
        "Publication_Year": _empty_if_none(paper.publication_year),
        "Article_Types": _serialize_list(paper.article_types),
        "MeSH_Terms": _serialize_list(paper.mesh_terms),
        "Keywords": _serialize_list(paper.keywords),
        "Authors": _serialize_list([author.full_name for author in paper.authors]),
        "Affiliations": _serialize_list(paper.affiliations),
        "Source_URL": paper.source_url,
        "Raw_Record_Path": paper.raw_record_path or "",
    }


def _pubmed_lead_to_dict(lead: PubMedLead) -> dict[str, Any]:
    return {
        "lead_id": lead.lead_id,
        "pi_full_name": lead.pi_full_name,
        "verified_email": lead.verified_email,
        "email_status": lead.email_status,
        "email_source_url": lead.email_source_url,
        "email_source_type": lead.email_source_type,
        "name_email_match_confidence": lead.name_email_match_confidence,
        "institution": lead.institution,
        "country": lead.country,
        "country_confidence": lead.country_confidence,
        "country_source": lead.country_source,
        "raw_affiliation": lead.raw_affiliation,
        "recent_publication_title": lead.recent_publication_title,
        "abstract": lead.abstract,
        "journal": lead.journal,
        "publication_year": lead.publication_year,
        "pmid": lead.pmid,
        "doi": lead.doi,
        "author_role": lead.author_role,
        "source_links": lead.source_links,
        "data_quality": lead.data_quality,
        "manual_review_required": lead.manual_review_required,
        "notes": lead.notes,
        "merge_status": lead.merge_status,
        "merge_reason": lead.merge_reason,
        "matched_keywords": lead.matched_keywords,
        "target_service_type": lead.target_service_type,
        "topic_match_score": lead.topic_match_score,
        "topic_match_reason": lead.topic_match_reason,
        "publication_recency_score": lead.publication_recency_score,
        "email_contactability_score": lead.email_contactability_score,
        "lead_score": lead.lead_score,
        "priority": lead.priority,
        "score_explanation": lead.score_explanation,
        "funding_activity_score": lead.funding_activity_score,
        "funding_activity_reason": lead.funding_activity_reason,
        "outsourcing_tendency_score": lead.outsourcing_tendency_score,
        "official_scoring_status": lead.official_scoring_status,
    }


def _pubmed_lead_to_csv_row(lead: PubMedLead) -> dict[str, Any]:
    return {
        "PI_Full_Name": lead.pi_full_name,
        "Verified_Email": lead.verified_email or "missing",
        "Email_Status": lead.email_status,
        "Email_Source_Type": lead.email_source_type,
        "Email_Source_URL": lead.email_source_url,
        "Name_Email_Match_Confidence": lead.name_email_match_confidence,
        "Institution": lead.institution or "unknown",
        "Country": lead.country,
        "Country_Confidence": lead.country_confidence,
        "Country_Source": lead.country_source,
        "Raw_Affiliation": lead.raw_affiliation or "",
        "Recent_Publication_Title": lead.recent_publication_title,
        "Abstract": lead.abstract,
        "Journal": lead.journal,
        "Publication_Year": _empty_if_none(lead.publication_year),
        "PMID": lead.pmid,
        "DOI": lead.doi or "",
        "Author_Role": lead.author_role,
        "Matched_Keywords": _serialize_list(lead.matched_keywords),
        "Target_Service_Type": lead.target_service_type or "",
        "Topic_Match_Score": lead.topic_match_score,
        "Publication_Recency_Score": lead.publication_recency_score,
        "Email_Contactability_Score": lead.email_contactability_score,
        "Lead_Score": lead.lead_score,
        "Priority": lead.priority,
        "Score_Explanation": lead.score_explanation,
        "Data_Quality": lead.data_quality,
        "Merge_Status": lead.merge_status,
        "Merge_Reason": lead.merge_reason or "",
        "Manual_Review_Required": lead.manual_review_required,
        "Funding_Activity_Score": _empty_if_none(lead.funding_activity_score),
        "Funding_Activity_Reason": lead.funding_activity_reason,
        "Outsourcing_Tendency_Score": _empty_if_none(
            lead.outsourcing_tendency_score
        ),
        "Official_Scoring_Status": lead.official_scoring_status,
        "Source_Links": _serialize_list(lead.source_links),
        "Notes": lead.notes,
    }


def _count_verified_email_leads(leads: list[PubMedLead]) -> int:
    return sum(
        1
        for lead in leads
        if lead.email_status == "verified_from_pubmed_affiliation"
        and lead.verified_email
    )


def _paths_to_dict(paths: Any) -> dict[str, str]:
    if paths is None:
        return {}

    if isinstance(paths, dict):
        return {
            str(key): str(value)
            for key, value in paths.items()
            if value is not None and str(value)
        }

    path_values: dict[str, str] = {}
    for field_name in getattr(paths, "__dataclass_fields__", {}):
        value = getattr(paths, field_name)
        if value is None:
            continue
        path_values[field_name] = str(value)
    return path_values


def _normalize_report_errors(
    errors: list[dict[str, Any] | str] | None,
) -> list[dict[str, str]]:
    normalized_errors: list[dict[str, str]] = []

    for error in errors or []:
        if isinstance(error, dict):
            normalized_errors.append(
                {
                    "stage": str(error.get("stage") or "unknown"),
                    "type": str(error.get("type") or "unknown"),
                    "message": str(error.get("message") or ""),
                }
            )
            continue

        normalized_errors.append(
            {
                "stage": "unknown",
                "type": "unknown",
                "message": str(error),
            }
        )

    return normalized_errors


def _deduplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _write_csv(
    path: Path,
    *,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")

    with temp_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(path)


def _serialize_list(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def _empty_if_none(value: Any) -> Any:
    return "" if value is None else value


def _write_text_atomically(path: Path, content: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def _safe_filename_part(value: str) -> str:
    safe_value = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE)
    safe_value = safe_value.strip("_")[:50]
    return safe_value or "search"
