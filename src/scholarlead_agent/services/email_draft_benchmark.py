"""Offline, versioned acceptance benchmark for Academic Cold Email drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from scholarlead_agent.ai.email_draft_quality import validate_email_draft_quality
from scholarlead_agent.ai.email_drafts import EmailDraftInput
from scholarlead_agent.capability_matching import CapabilityMatchItem


DEFAULT_EMAIL_DRAFT_BENCHMARK_PATH = Path(
    "data/benchmarks/email_draft_v2_acceptance.json"
)


@dataclass(frozen=True)
class EmailDraftBenchmarkCase:
    case_id: str
    title: str
    abstract: str
    keywords: list[str]
    expected_draft_mode: str
    expected_quality_status: str
    candidate_capabilities: list[CapabilityMatchItem]
    subject: str
    body: str
    legacy_v1_issue: str | None = None


@dataclass(frozen=True)
class EmailDraftBenchmarkResult:
    benchmark_version: str
    total_cases: int
    passed_cases: int
    failed_cases: list[dict[str, Any]] = field(default_factory=list)
    mode_counts: dict[str, int] = field(default_factory=dict)
    quality_counts: dict[str, int] = field(default_factory=dict)
    legacy_v1_issue_counts: dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.failed_cases

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": list(self.failed_cases),
            "mode_counts": dict(self.mode_counts),
            "quality_counts": dict(self.quality_counts),
            "legacy_v1_issue_counts": dict(self.legacy_v1_issue_counts),
            "passed": self.passed,
        }


def load_email_draft_benchmark(
    path: Path | str = DEFAULT_EMAIL_DRAFT_BENCHMARK_PATH,
) -> tuple[str, list[EmailDraftBenchmarkCase]]:
    """Load a manually labeled local benchmark without model or network access."""

    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("email draft benchmark must be a JSON object")
    version = _required_text(payload, "benchmark_version")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 20:
        raise ValueError("email draft benchmark must contain at least 20 cases")
    return version, [_case_from_dict(item) for item in cases_raw]


def run_email_draft_benchmark(
    path: Path | str = DEFAULT_EMAIL_DRAFT_BENCHMARK_PATH,
) -> EmailDraftBenchmarkResult:
    """Run the deterministic benchmark against its approved fixture drafts."""

    version, cases = load_email_draft_benchmark(path)
    failures: list[dict[str, Any]] = []
    mode_counts: dict[str, int] = {}
    quality_counts: dict[str, int] = {}
    legacy_issue_counts: dict[str, int] = {}
    for case in cases:
        evidence = EmailDraftInput(
            lead_id=case.case_id,
            pi_full_name="Benchmark Researcher",
            recent_publication_title=case.title,
            abstract=case.abstract,
            source_url=f"https://example.invalid/{case.case_id}",
            matched_keywords=case.keywords,
            candidate_capabilities=case.candidate_capabilities,
            capability_match_status=("partial_match" if case.candidate_capabilities else "no_match"),
            draft_mode=case.expected_draft_mode,
        )
        report = validate_email_draft_quality(
            evidence,
            subject=case.subject,
            body=case.body,
            strict_json_output=True,
        )
        mode_counts[case.expected_draft_mode] = mode_counts.get(case.expected_draft_mode, 0) + 1
        quality_counts[report.status] = quality_counts.get(report.status, 0) + 1
        if case.legacy_v1_issue:
            legacy_issue_counts[case.legacy_v1_issue] = (
                legacy_issue_counts.get(case.legacy_v1_issue, 0) + 1
            )
        if report.status != case.expected_quality_status:
            failures.append(
                {
                    "case_id": case.case_id,
                    "expected_quality_status": case.expected_quality_status,
                    "actual_quality_status": report.status,
                    "failure_reasons": report.failure_reasons,
                    "warnings": report.warnings,
                }
            )
    return EmailDraftBenchmarkResult(
        benchmark_version=version,
        total_cases=len(cases),
        passed_cases=len(cases) - len(failures),
        failed_cases=failures,
        mode_counts=mode_counts,
        quality_counts=quality_counts,
        legacy_v1_issue_counts=legacy_issue_counts,
    )


def _case_from_dict(value: Any) -> EmailDraftBenchmarkCase:
    if not isinstance(value, dict):
        raise ValueError("each benchmark case must be an object")
    capability = value.get("candidate_capability")
    capabilities: list[CapabilityMatchItem] = []
    if capability is not None:
        if not isinstance(capability, dict):
            raise ValueError("candidate_capability must be an object")
        capabilities.append(
            CapabilityMatchItem(
                capability_id=_required_text(capability, "capability_id"),
                capability_name=_required_text(capability, "capability_name"),
                match_score=0.5,
                match_reason="benchmark evidence match",
                matched_terms=_required_text_list(capability, "matched_terms"),
                evidence=["benchmark labeled evidence"],
            )
        )
    draft = value.get("draft")
    if not isinstance(draft, dict):
        raise ValueError("benchmark draft must be an object")
    return EmailDraftBenchmarkCase(
        case_id=_required_text(value, "case_id"),
        title=_required_text(value, "title"),
        abstract=_required_text(value, "abstract"),
        keywords=_required_text_list(value, "keywords"),
        expected_draft_mode=_required_text(value, "expected_draft_mode"),
        expected_quality_status=_required_text(value, "expected_quality_status"),
        candidate_capabilities=capabilities,
        subject=_required_text(draft, "subject"),
        body=_required_text(draft, "body"),
        legacy_v1_issue=_optional_text(value.get("legacy_v1_issue")),
    )


def _required_text(value: dict[str, Any], field_name: str) -> str:
    text = _optional_text(value.get(field_name))
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _required_text_list(value: dict[str, Any], field_name: str) -> list[str]:
    raw = value.get(field_name)
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) and item.strip() for item in raw):
        raise ValueError(f"{field_name} must be a non-empty text list")
    return [item.strip() for item in raw]


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
