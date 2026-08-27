"""Result Package v1 export helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from scholarlead_agent.ai.email_drafts import EmailDraft, email_draft_to_dict
from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper
from scholarlead_agent.services.pubmed_service import PubMedRunResult


RESULT_PACKAGE_VERSION = "result-package-v1"
SCORING_VERSION = "draft-v1"
SCORING_STATUS = "provisional"
DEFAULT_RESULT_PACKAGE_DIR = Path("data/processed/result_packages")


@dataclass(frozen=True)
class ResultPackagePaths:
    """Files produced for one Result Package."""

    package_dir: Path
    workbook_xlsx: Path
    customers_csv: Path
    papers_csv: Path
    funding_csv: Path
    evidence_csv: Path
    service_matches_csv: Path
    email_drafts_csv: Path
    task_summary_json: Path


@dataclass(frozen=True)
class ResultPackage:
    """Structured result for a generated Result Package."""

    task_id: str
    package_id: str
    status: str
    paths: ResultPackagePaths
    task_summary: dict[str, Any]
    row_counts: dict[str, int]


def build_result_package_from_pubmed_result(
    result: PubMedRunResult,
    *,
    output_dir: Path | str = DEFAULT_RESULT_PACKAGE_DIR,
    funding_rows: list[dict[str, Any]] | None = None,
    service_match_rows: list[dict[str, Any]] | None = None,
    email_drafts: list[EmailDraft | dict[str, Any]] | None = None,
    created_at: str | None = None,
) -> ResultPackage:
    """Export one PubMed task into a Result Package v1 directory.

    This function only formats already available task artifacts. It does not
    rerun PubMed, ServiceMatcher, scoring, email generation, or entity merging.
    """

    package_created_at = created_at or datetime.now().isoformat(timespec="seconds")
    package_id = f"TASK_{_safe_id(result.task_id)}"
    paths = _build_result_package_paths(Path(output_dir), package_id)
    drafts = [_draft_to_dict(draft) for draft in email_drafts or []]
    service_rows = _merge_service_match_rows(
        task_id=result.task_id,
        explicit_rows=service_match_rows or [],
        draft_rows=drafts,
    )

    customer_rows = _customer_rows(result, service_rows=service_rows)
    paper_rows = _paper_rows(result.task_id, result.papers)
    funding_output_rows = [_normalize_row(row, FUNDING_FIELDS) for row in (funding_rows or [])]
    evidence_rows = _evidence_rows(result)
    email_draft_rows = _email_draft_rows(result.task_id, drafts)
    summary = _task_summary(
        result,
        package_id=package_id,
        created_at=package_created_at,
        row_counts={
            "customers": len(customer_rows),
            "papers": len(paper_rows),
            "funding": len(funding_output_rows),
            "evidence": len(evidence_rows),
            "service_matches": len(service_rows),
            "email_drafts": len(email_draft_rows),
        },
    )
    summary_rows = _summary_rows(summary)

    _write_csv(paths.customers_csv, CUSTOMERS_FIELDS, customer_rows)
    _write_csv(paths.papers_csv, PAPERS_FIELDS, paper_rows)
    _write_csv(paths.funding_csv, FUNDING_FIELDS, funding_output_rows)
    _write_csv(paths.evidence_csv, EVIDENCE_FIELDS, evidence_rows)
    _write_csv(paths.service_matches_csv, SERVICE_MATCH_FIELDS, service_rows)
    _write_csv(paths.email_drafts_csv, EMAIL_DRAFT_FIELDS, email_draft_rows)
    _write_json(paths.task_summary_json, summary)
    _write_xlsx(
        paths.workbook_xlsx,
        {
            "Customers": (CUSTOMERS_FIELDS, customer_rows),
            "Papers": (PAPERS_FIELDS, paper_rows),
            "Funding": (FUNDING_FIELDS, funding_output_rows),
            "Evidence": (EVIDENCE_FIELDS, evidence_rows),
            "Service_Matches": (SERVICE_MATCH_FIELDS, service_rows),
            "Email_Drafts": (EMAIL_DRAFT_FIELDS, email_draft_rows),
            "Task_Summary": (["Field", "Value"], summary_rows),
        },
    )

    return ResultPackage(
        task_id=result.task_id,
        package_id=package_id,
        status="success",
        paths=paths,
        task_summary=summary,
        row_counts=summary["row_counts"],
    )


CUSTOMERS_FIELDS = [
    "Task_ID",
    "Researcher_ID",
    "Lead_ID",
    "PI_Name",
    "Verified_Email",
    "Email_Status",
    "Email_Source",
    "Institution",
    "Country",
    "Recent_Publication_Title",
    "PMID",
    "DOI",
    "Funding_Status",
    "Lead_Score",
    "Priority",
    "Scoring_Version",
    "Scoring_Status",
    "Recommendation_Reason",
    "Matched_Service_ID",
    "Matched_Service_Name",
    "Service_Match_Score",
    "Manual_Review_Required",
    "Source_Links",
]

PAPERS_FIELDS = [
    "Task_ID",
    "PMID",
    "DOI",
    "Title",
    "Journal",
    "Publication_Date",
    "Publication_Year",
    "Authors",
    "Keywords",
    "Source_URL",
    "Raw_Record_Path",
]

FUNDING_FIELDS = [
    "Task_ID",
    "Researcher_ID",
    "Lead_ID",
    "Funding_ID",
    "Agency",
    "Project_Title",
    "Fiscal_Year",
    "Amount",
    "Source_URL",
    "Evidence",
]

EVIDENCE_FIELDS = [
    "Task_ID",
    "Researcher_ID",
    "Lead_ID",
    "Source_Name",
    "Source_Type",
    "Source_ID",
    "Source_URL",
    "Field_Name",
    "Field_Value",
    "Confidence",
    "Raw_Record_Path",
    "Note",
]

SERVICE_MATCH_FIELDS = [
    "Task_ID",
    "Researcher_ID",
    "Lead_ID",
    "Service_ID",
    "Service_Name",
    "Match_Score",
    "Match_Status",
    "Match_Reason",
    "Matched_Terms",
    "Evidence",
    "Catalog_Version",
    "Matcher_Version",
    "Created_At",
]

EMAIL_DRAFT_FIELDS = [
    "Task_ID",
    "Researcher_ID",
    "Lead_ID",
    "Recipient_Name",
    "Verified_Email",
    "Email_Status",
    "Draft_Status",
    "Subject",
    "Body",
    "Target_Service_Type",
    "Matched_Service_ID",
    "Matched_Service_Name",
    "Service_Match_Score",
    "Model_Name",
    "Generated_At",
    "Can_Send",
    "Warnings",
]


def _build_result_package_paths(
    output_dir: Path,
    package_id: str,
) -> ResultPackagePaths:
    package_dir = output_dir / package_id
    return ResultPackagePaths(
        package_dir=package_dir,
        workbook_xlsx=package_dir / "scholarlead_results.xlsx",
        customers_csv=package_dir / "customers.csv",
        papers_csv=package_dir / "papers.csv",
        funding_csv=package_dir / "funding.csv",
        evidence_csv=package_dir / "evidence.csv",
        service_matches_csv=package_dir / "service_matches.csv",
        email_drafts_csv=package_dir / "email_drafts.csv",
        task_summary_json=package_dir / "task_summary.json",
    )


def _customer_rows(
    result: PubMedRunResult,
    *,
    service_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    service_by_lead_id = {
        str(row.get("Lead_ID") or ""): row
        for row in service_rows
        if row.get("Lead_ID")
    }
    rows: list[dict[str, Any]] = []
    for lead in result.leads:
        service = service_by_lead_id.get(lead.lead_id, {})
        rows.append(
            {
                "Task_ID": result.task_id,
                "Researcher_ID": researcher_id_from_lead(lead),
                "Lead_ID": lead.lead_id,
                "PI_Name": lead.pi_full_name,
                "Verified_Email": lead.verified_email or "missing",
                "Email_Status": lead.email_status,
                "Email_Source": lead.email_source_type,
                "Institution": lead.institution or "unknown",
                "Country": lead.country or "unknown",
                "Recent_Publication_Title": lead.recent_publication_title,
                "PMID": lead.pmid,
                "DOI": lead.doi or "",
                "Funding_Status": lead.funding_activity_reason,
                "Lead_Score": lead.lead_score,
                "Priority": lead.priority,
                "Scoring_Version": SCORING_VERSION,
                "Scoring_Status": SCORING_STATUS,
                "Recommendation_Reason": lead.score_explanation,
                "Matched_Service_ID": service.get("Service_ID", ""),
                "Matched_Service_Name": service.get("Service_Name", ""),
                "Service_Match_Score": service.get("Match_Score", ""),
                "Manual_Review_Required": lead.manual_review_required,
                "Source_Links": _json_list(lead.source_links),
            }
        )
    return rows


def _paper_rows(task_id: str, papers: list[PubMedPaper]) -> list[dict[str, Any]]:
    return [
        {
            "Task_ID": task_id,
            "PMID": paper.pmid,
            "DOI": paper.doi or "",
            "Title": paper.title,
            "Journal": paper.journal,
            "Publication_Date": paper.publication_date,
            "Publication_Year": _empty_if_none(paper.publication_year),
            "Authors": _json_list([author.full_name for author in paper.authors]),
            "Keywords": _json_list(paper.keywords),
            "Source_URL": paper.source_url,
            "Raw_Record_Path": paper.raw_record_path or "",
        }
        for paper in papers
    ]


def _evidence_rows(result: PubMedRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lead in result.leads:
        researcher_id = researcher_id_from_lead(lead)
        rows.extend(
            [
                _evidence_row(
                    result.task_id,
                    researcher_id,
                    lead.lead_id,
                    source_type="pubmed_affiliation",
                    source_id=lead.pmid,
                    source_url=lead.email_source_url,
                    field_name="verified_email",
                    field_value=lead.verified_email or "",
                    confidence=lead.name_email_match_confidence,
                    note=f"email_status={lead.email_status}",
                ),
                _evidence_row(
                    result.task_id,
                    researcher_id,
                    lead.lead_id,
                    source_type="pubmed_affiliation",
                    source_id=lead.pmid,
                    source_url=lead.source_links[0] if lead.source_links else "",
                    field_name="institution",
                    field_value=lead.institution or "",
                    confidence="medium",
                    note="institution from affiliation parser",
                ),
                _evidence_row(
                    result.task_id,
                    researcher_id,
                    lead.lead_id,
                    source_type="pubmed_affiliation",
                    source_id=lead.pmid,
                    source_url=lead.source_links[0] if lead.source_links else "",
                    field_name="country",
                    field_value=lead.country,
                    confidence=lead.country_confidence,
                    note=lead.country_source,
                ),
                _evidence_row(
                    result.task_id,
                    researcher_id,
                    lead.lead_id,
                    source_type="pubmed_scoring",
                    source_id=lead.lead_id,
                    source_url=lead.source_links[0] if lead.source_links else "",
                    field_name="lead_score",
                    field_value=str(lead.lead_score),
                    confidence="medium",
                    note=lead.score_explanation,
                ),
            ]
        )
    return [row for row in rows if row["Field_Value"]]


def _evidence_row(
    task_id: str,
    researcher_id: str,
    lead_id: str,
    *,
    source_type: str,
    source_id: str,
    source_url: str,
    field_name: str,
    field_value: str,
    confidence: str,
    raw_record_path: str = "",
    note: str = "",
) -> dict[str, Any]:
    return {
        "Task_ID": task_id,
        "Researcher_ID": researcher_id,
        "Lead_ID": lead_id,
        "Source_Name": "pubmed",
        "Source_Type": source_type,
        "Source_ID": source_id,
        "Source_URL": source_url,
        "Field_Name": field_name,
        "Field_Value": field_value,
        "Confidence": confidence or "unknown",
        "Raw_Record_Path": raw_record_path,
        "Note": note,
    }


def _merge_service_match_rows(
    *,
    task_id: str,
    explicit_rows: list[dict[str, Any]],
    draft_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [_normalize_row(row, SERVICE_MATCH_FIELDS) for row in explicit_rows]
    known_leads = {str(row.get("Lead_ID") or "") for row in rows}
    for draft in draft_rows:
        lead_id = str(draft.get("lead_id") or "")
        if not lead_id or lead_id in known_leads:
            continue
        evidence = draft.get("evidence") if isinstance(draft.get("evidence"), dict) else {}
        matched_service = (
            evidence.get("matched_service")
            if isinstance(evidence.get("matched_service"), dict)
            else {}
        )
        service_id = matched_service.get("service_id")
        service_name = matched_service.get("service_name")
        if not service_id and not service_name:
            continue
        rows.append(
            {
                "Task_ID": task_id,
                "Researcher_ID": researcher_id_from_draft(draft),
                "Lead_ID": lead_id,
                "Service_ID": service_id or "",
                "Service_Name": service_name or "",
                "Match_Score": _empty_if_none(matched_service.get("match_score")),
                "Match_Status": matched_service.get("status") or "",
                "Match_Reason": matched_service.get("match_reason") or "",
                "Matched_Terms": _json_list(matched_service.get("matched_terms") or []),
                "Evidence": _json_list(matched_service.get("evidence") or []),
                "Catalog_Version": matched_service.get("catalog_version") or "",
                "Matcher_Version": matched_service.get("matcher_version") or "",
                "Created_At": draft.get("generated_at") or "",
            }
        )
        known_leads.add(lead_id)
    return [_normalize_row(row, SERVICE_MATCH_FIELDS) for row in rows]


def _email_draft_rows(
    task_id: str,
    drafts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for draft in drafts:
        evidence = draft.get("evidence") if isinstance(draft.get("evidence"), dict) else {}
        matched_service = (
            evidence.get("matched_service")
            if isinstance(evidence.get("matched_service"), dict)
            else {}
        )
        rows.append(
            {
                "Task_ID": task_id,
                "Researcher_ID": researcher_id_from_draft(draft),
                "Lead_ID": draft.get("lead_id") or "",
                "Recipient_Name": draft.get("recipient_name") or "",
                "Verified_Email": draft.get("verified_email") or "missing",
                "Email_Status": draft.get("email_status") or "",
                "Draft_Status": draft.get("draft_status") or "",
                "Subject": draft.get("subject") or "",
                "Body": draft.get("body") or "",
                "Target_Service_Type": draft.get("target_service_type") or "",
                "Matched_Service_ID": matched_service.get("service_id") or "",
                "Matched_Service_Name": matched_service.get("service_name") or "",
                "Service_Match_Score": _empty_if_none(matched_service.get("match_score")),
                "Model_Name": draft.get("model_name") or "",
                "Generated_At": draft.get("generated_at") or "",
                "Can_Send": draft.get("can_send"),
                "Warnings": _json_list(draft.get("warnings") or []),
            }
        )
    return [_normalize_row(row, EMAIL_DRAFT_FIELDS) for row in rows]


def _task_summary(
    result: PubMedRunResult,
    *,
    package_id: str,
    created_at: str,
    row_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "package_id": package_id,
        "package_version": RESULT_PACKAGE_VERSION,
        "task_id": result.task_id,
        "source": "pubmed",
        "status": result.status,
        "query": result.search_params.query,
        "from_date": result.search_params.from_date,
        "to_date": result.search_params.to_date,
        "max_results": result.search_params.max_results,
        "created_at": created_at,
        "run_report_path": str(result.run_report_path),
        "scoring_version": SCORING_VERSION,
        "scoring_status": SCORING_STATUS,
        "scoring_note": "Current Lead_Score is draft/provisional, not official production scoring.",
        "row_counts": row_counts,
        "source_files": {
            "raw_files": result.raw_files,
            "processed_files": result.processed_files,
        },
    }


def researcher_id_from_lead(lead: PubMedLead) -> str:
    """Build a stable researcher id for cross-sheet linking."""

    email = (lead.verified_email or "").strip().lower()
    if email and lead.email_status != "missing":
        return f"researcher-email-{_slug(email)}"
    return f"researcher-lead-{_slug(lead.lead_id)}"


def researcher_id_from_draft(draft: dict[str, Any]) -> str:
    email = str(draft.get("verified_email") or "").strip().lower()
    if email and email != "missing":
        return f"researcher-email-{_slug(email)}"
    return f"researcher-lead-{_slug(str(draft.get('lead_id') or 'unknown'))}"


def _draft_to_dict(draft: EmailDraft | dict[str, Any]) -> dict[str, Any]:
    if isinstance(draft, EmailDraft):
        return email_draft_to_dict(draft)
    if isinstance(draft, dict):
        return dict(draft)
    raise ValueError("email_drafts must contain EmailDraft or dictionary items")


def _normalize_row(row: dict[str, Any], fieldnames: list[str]) -> dict[str, Any]:
    return {field: _empty_if_none(row.get(field)) for field in fieldnames}


def _summary_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in summary.items():
        rows.append(
            {
                "Field": key,
                "Value": json.dumps(value, ensure_ascii=False, sort_keys=True)
                if isinstance(value, dict | list)
                else _empty_if_none(value),
            }
        )
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _write_xlsx(
    path: Path,
    sheets: dict[str, tuple[list[str], list[dict[str, Any]]]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with ZipFile(temp_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(list(sheets)))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (_, (fieldnames, rows)) in enumerate(sheets.items(), start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _worksheet_xml(fieldnames, rows),
            )
    temp_path.replace(path)


def _content_types_xml(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{sheet_overrides}</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets_xml = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets_xml}</sheets></workbook>"
    )


def _workbook_rels_xml(sheet_count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    rels += (
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{rels}</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        "</styleSheet>"
    )


def _worksheet_xml(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    all_rows = [fieldnames] + [
        [row.get(field, "") for field in fieldnames]
        for row in rows
    ]
    rows_xml = "".join(
        f'<row r="{row_index}">'
        + "".join(
            _cell_xml(row_index, column_index, value)
            for column_index, value in enumerate(row, start=1)
        )
        + "</row>"
        for row_index, row in enumerate(all_rows, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{rows_xml}</sheetData></worksheet>"
    )


def _cell_xml(row_index: int, column_index: int, value: Any) -> str:
    cell_ref = f"{_column_name(column_index)}{row_index}"
    text = escape(str(_empty_if_none(value)))
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _json_list(values: Any) -> str:
    if values is None:
        values = []
    if not isinstance(values, list):
        values = [values]
    return json.dumps(values, ensure_ascii=False)


def _empty_if_none(value: Any) -> Any:
    return "" if value is None else value


def _safe_id(value: str) -> str:
    return _slug(value).replace("-", "_")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"
