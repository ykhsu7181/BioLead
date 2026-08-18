"""Reusable PubMed first-round workflow service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from scholarlead_agent.pubmed_affiliation import enrich_leads_affiliation
from scholarlead_agent.pubmed_client import PubMedClient
from scholarlead_agent.pubmed_leads import (
    build_leads_from_papers,
    deduplicate_pubmed_leads,
)
from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper, PubMedSearchParams
from scholarlead_agent.pubmed_parser import deduplicate_pubmed_papers, parse_pubmed_xml
from scholarlead_agent.pubmed_scoring import (
    enrich_leads_keyword_match,
    score_pubmed_leads,
)
from scholarlead_agent.pubmed_storage import (
    PubMedProcessedOutputPaths,
    PubMedRawOutputPaths,
    build_pubmed_processed_output_paths,
    build_pubmed_raw_output_paths,
    build_pubmed_request_meta,
    build_pubmed_run_report,
    build_pubmed_run_report_path,
    save_pubmed_efetch_xml,
    save_pubmed_esearch_response,
    save_pubmed_processed_outputs,
    save_pubmed_request_meta,
    save_pubmed_run_report,
)


class PubMedWorkflowClient(Protocol):
    """Protocol for PubMed clients used by the service."""

    def esearch(self, params: PubMedSearchParams) -> dict[str, Any]:
        """Return the raw PubMed ESearch JSON response."""

    def efetch(self, pmids: list[str]) -> str:
        """Return the raw PubMed EFetch XML response."""


@dataclass(frozen=True)
class PubMedRunResult:
    """Structured result from one PubMed first-round run."""

    task_id: str
    status: str
    pmids: list[str]
    papers: list[PubMedPaper]
    leads: list[PubMedLead]
    raw_paths: PubMedRawOutputPaths
    processed_paths: PubMedProcessedOutputPaths
    run_report_path: Path
    run_report: dict[str, Any]
    errors: list[dict[str, str]]


def run_pubmed_search(
    params: PubMedSearchParams,
    *,
    client: PubMedWorkflowClient | None = None,
    timestamp: str | None = None,
    task_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> PubMedRunResult:
    """Run the PubMed first-round workflow end to end."""

    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_task_id = task_id or f"pubmed-{run_timestamp}"
    run_started_at = started_at or datetime.now().isoformat(timespec="seconds")
    pubmed_client = client or PubMedClient()

    raw_paths = build_pubmed_raw_output_paths(
        query=params.query,
        raw_dir=params.raw_dir,
        timestamp=run_timestamp,
    )
    processed_paths = build_pubmed_processed_output_paths(
        query=params.query,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    )
    run_report_path = build_pubmed_run_report_path(
        query=params.query,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    ).run_report_json

    errors: list[dict[str, str]] = []
    pmids: list[str] = []
    papers: list[PubMedPaper] = []
    leads: list[PubMedLead] = []
    status = "success"

    try:
        esearch_response = pubmed_client.esearch(params)
        save_pubmed_esearch_response(esearch_response, raw_paths.esearch_json)
        pmids = extract_pmids_from_esearch_response(esearch_response)
    except Exception as error:
        errors.append(_build_error("esearch", error))
        status = "failed"
        run_report = _save_report(
            params=params,
            task_id=run_task_id,
            pmids=pmids,
            papers=papers,
            leads=leads,
            raw_paths=raw_paths,
            processed_paths=None,
            errors=errors,
            started_at=run_started_at,
            finished_at=finished_at,
            status=status,
            run_report_path=run_report_path,
        )
        return _build_run_result(
            task_id=run_task_id,
            status=status,
            pmids=pmids,
            papers=papers,
            leads=leads,
            raw_paths=raw_paths,
            processed_paths=processed_paths,
            run_report_path=run_report_path,
            run_report=run_report,
            errors=errors,
        )

    try:
        if pmids:
            efetch_xml = pubmed_client.efetch(pmids)
            save_pubmed_efetch_xml(efetch_xml, raw_paths.efetch_xml)
        else:
            efetch_xml = "<PubmedArticleSet />"
            save_pubmed_efetch_xml(efetch_xml, raw_paths.efetch_xml)
    except Exception as error:
        errors.append(_build_error("efetch", error))
        status = "partial_failure"
        _save_request_meta(params, raw_paths, status=status, errors=errors)
        run_report = _save_report(
            params=params,
            task_id=run_task_id,
            pmids=pmids,
            papers=papers,
            leads=leads,
            raw_paths=raw_paths,
            processed_paths=None,
            errors=errors,
            started_at=run_started_at,
            finished_at=finished_at,
            status=status,
            run_report_path=run_report_path,
        )
        return _build_run_result(
            task_id=run_task_id,
            status=status,
            pmids=pmids,
            papers=papers,
            leads=leads,
            raw_paths=raw_paths,
            processed_paths=processed_paths,
            run_report_path=run_report_path,
            run_report=run_report,
            errors=errors,
        )

    _save_request_meta(params, raw_paths, status=status, errors=errors)

    try:
        parsed_papers = parse_pubmed_xml(
            efetch_xml,
            raw_record_path=raw_paths.efetch_xml,
        )
        papers = deduplicate_pubmed_papers(parsed_papers)
        leads = build_leads_from_papers(papers)
        leads = deduplicate_pubmed_leads(leads)
        leads = enrich_leads_affiliation(leads)
        leads = enrich_leads_keyword_match(
            leads,
            query=params.query,
            service_type=params.service_type,
            paper_by_pmid={paper.pmid: paper for paper in papers},
        )
        leads = score_pubmed_leads(leads)
        save_pubmed_processed_outputs(
            papers=papers,
            leads=leads,
            paths=processed_paths,
        )
    except Exception as error:
        errors.append(_build_error("processing", error))
        status = "partial_failure"

    run_report = _save_report(
        params=params,
        task_id=run_task_id,
        pmids=pmids,
        papers=papers,
        leads=leads,
        raw_paths=raw_paths,
        processed_paths=processed_paths if status == "success" else None,
        errors=errors,
        started_at=run_started_at,
        finished_at=finished_at,
        status=status,
        run_report_path=run_report_path,
    )

    return _build_run_result(
        task_id=run_task_id,
        status=status,
        pmids=pmids,
        papers=papers,
        leads=leads,
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
    )


def extract_pmids_from_esearch_response(raw_response: dict[str, Any]) -> list[str]:
    """Extract normalized PMIDs from a PubMed ESearch response."""

    idlist = raw_response.get("esearchresult", {}).get("idlist", [])
    if not isinstance(idlist, list):
        return []

    pmids: list[str] = []
    seen: set[str] = set()
    for value in idlist:
        if not isinstance(value, str):
            continue
        pmid = value.strip()
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        pmids.append(pmid)

    return pmids


def _save_request_meta(
    params: PubMedSearchParams,
    raw_paths: PubMedRawOutputPaths,
    *,
    status: str,
    errors: list[dict[str, str]],
) -> None:
    request_meta = build_pubmed_request_meta(
        params=params,
        paths=raw_paths,
        status=status,
        errors=[error["message"] for error in errors],
    )
    save_pubmed_request_meta(request_meta, raw_paths.request_meta_json)


def _save_report(
    *,
    params: PubMedSearchParams,
    task_id: str,
    pmids: list[str],
    papers: list[PubMedPaper],
    leads: list[PubMedLead],
    raw_paths: PubMedRawOutputPaths,
    processed_paths: PubMedProcessedOutputPaths | None,
    errors: list[dict[str, str]],
    started_at: str,
    finished_at: str | None,
    status: str,
    run_report_path: Path,
) -> dict[str, Any]:
    report = build_pubmed_run_report(
        params=params,
        task_id=task_id,
        pmids=pmids,
        papers=papers,
        leads=leads,
        raw_files=raw_paths,
        processed_files=processed_paths,
        errors=errors,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
    )
    save_pubmed_run_report(report, run_report_path)
    return report


def _build_run_result(
    *,
    task_id: str,
    status: str,
    pmids: list[str],
    papers: list[PubMedPaper],
    leads: list[PubMedLead],
    raw_paths: PubMedRawOutputPaths,
    processed_paths: PubMedProcessedOutputPaths,
    run_report_path: Path,
    run_report: dict[str, Any],
    errors: list[dict[str, str]],
) -> PubMedRunResult:
    return PubMedRunResult(
        task_id=task_id,
        status=status,
        pmids=pmids,
        papers=papers,
        leads=leads,
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
    )


def _build_error(stage: str, error: Exception) -> dict[str, str]:
    return {
        "stage": stage,
        "type": error.__class__.__name__,
        "message": str(error),
    }
