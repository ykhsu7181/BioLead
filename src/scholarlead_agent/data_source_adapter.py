"""Specification helpers for adding new data sources.

Stage 38 does not implement another external source. It defines the minimum
contract future sources must satisfy before being exposed through Agent tools,
API routes, or frontend screens.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


REQUIRED_ADAPTER_COMPONENTS = (
    "client",
    "parser",
    "service",
    "tool_adapter",
    "unified_converter",
    "raw_storage",
    "processed_export",
    "mocked_tests",
    "run_report",
    "source_metadata",
)

FORBIDDEN_BYPASSES = (
    "frontend_direct_external_api",
    "fastapi_route_direct_external_api",
    "streamlit_direct_external_api",
    "skip_raw_storage",
    "skip_evidence",
    "direct_email_generation_from_raw_fields",
    "register_tool_without_tests",
    "llm_guess_missing_email",
    "llm_guess_funding_or_identity",
)


@dataclass(frozen=True)
class DataSourceAdapterSpec:
    """Declarative checklist for one future data source adapter."""

    source_name: str
    client_module: str
    parser_module: str
    service_module: str
    tool_module: str
    converter_function: str
    raw_storage_dir: str
    processed_storage_dir: str
    test_modules: list[str]
    run_report_fields: list[str]
    source_metadata_fields: list[str]
    allowed_output_models: list[str]
    license_or_terms_note: str
    rate_limit_note: str | None = None
    access_restriction_note: str | None = None
    registered_as_agent_tool: bool = False
    known_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the adapter spec to a serializable dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class AdapterValidationResult:
    """Validation result for a data source adapter spec."""

    valid: bool
    missing_components: list[str] = field(default_factory=list)
    missing_metadata_fields: list[str] = field(default_factory=list)
    missing_run_report_fields: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to a serializable dictionary."""

        return asdict(self)


def validate_data_source_adapter_spec(
    spec: DataSourceAdapterSpec,
) -> AdapterValidationResult:
    """Validate a future data source adapter against the Stage 38 contract."""

    missing_components: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    component_values = {
        "client": spec.client_module,
        "parser": spec.parser_module,
        "service": spec.service_module,
        "tool_adapter": spec.tool_module,
        "unified_converter": spec.converter_function,
        "raw_storage": spec.raw_storage_dir,
        "processed_export": spec.processed_storage_dir,
        "mocked_tests": spec.test_modules,
        "run_report": spec.run_report_fields,
        "source_metadata": spec.source_metadata_fields,
    }
    for component in REQUIRED_ADAPTER_COMPONENTS:
        value = component_values[component]
        if not value:
            missing_components.append(component)

    missing_metadata_fields = [
        field_name
        for field_name in required_source_metadata_fields()
        if field_name not in set(spec.source_metadata_fields)
    ]
    missing_run_report_fields = [
        field_name
        for field_name in required_run_report_fields()
        if field_name not in set(spec.run_report_fields)
    ]

    if spec.registered_as_agent_tool and not spec.test_modules:
        blockers.append("agent_tool_requires_mocked_tests")
    if "EvidenceRecord" not in spec.allowed_output_models:
        blockers.append("adapter_must_output_evidence_records")
    if not any(model.startswith("Unified") for model in spec.allowed_output_models):
        blockers.append("adapter_must_output_at_least_one_unified_model")
    if not spec.license_or_terms_note.strip():
        blockers.append("license_or_terms_note_required")
    if missing_components:
        blockers.append("missing_required_adapter_components")
    if missing_metadata_fields:
        blockers.append("missing_required_source_metadata")
    if missing_run_report_fields:
        blockers.append("missing_required_run_report_fields")
    if not spec.known_limitations:
        warnings.append("known_limitations_should_be_documented")
    if not spec.rate_limit_note:
        warnings.append("rate_limit_note_should_be_documented")

    return AdapterValidationResult(
        valid=not blockers,
        missing_components=missing_components,
        missing_metadata_fields=missing_metadata_fields,
        missing_run_report_fields=missing_run_report_fields,
        blockers=blockers,
        warnings=warnings,
    )


def required_source_metadata_fields() -> list[str]:
    """Return required source metadata fields for all new data sources."""

    return [
        "source_name",
        "source_record_id",
        "source_url",
        "raw_file_path",
        "collected_at",
        "parser_version",
        "converter_version",
        "confidence",
        "license_or_terms_note",
    ]


def required_run_report_fields() -> list[str]:
    """Return required run report fields for source collection tasks."""

    return [
        "task_id",
        "source_name",
        "query",
        "status",
        "started_at",
        "finished_at",
        "raw_files",
        "processed_files",
        "record_count",
        "errors",
        "source_metadata",
    ]


def forbidden_bypasses() -> list[str]:
    """Return actions that new data source implementations must not take."""

    return list(FORBIDDEN_BYPASSES)


def example_data_source_adapter_spec(source_name: str = "example_source") -> DataSourceAdapterSpec:
    """Return a complete example spec for documentation and tests."""

    return DataSourceAdapterSpec(
        source_name=source_name,
        client_module=f"scholarlead_agent.{source_name}_client",
        parser_module=f"scholarlead_agent.{source_name}_parser",
        service_module=f"scholarlead_agent.services.{source_name}_service",
        tool_module=f"scholarlead_agent.tools.{source_name}_tool",
        converter_function=f"{source_name}_record_to_unified_model",
        raw_storage_dir=f"data/raw/{source_name}",
        processed_storage_dir=f"data/processed/{source_name}",
        test_modules=[
            f"tests/test_{source_name}_client.py",
            f"tests/test_{source_name}_parser.py",
            f"tests/test_{source_name}_service.py",
            f"tests/test_{source_name}_tool.py",
        ],
        run_report_fields=required_run_report_fields(),
        source_metadata_fields=required_source_metadata_fields(),
        allowed_output_models=["UnifiedPaper", "EvidenceRecord"],
        license_or_terms_note="Document source terms before collection.",
        rate_limit_note="Document rate limits and retry rules before collection.",
        access_restriction_note="Do not bypass login, CAPTCHA, robots, or license restrictions.",
        registered_as_agent_tool=False,
        known_limitations=["Example spec only; no real network collection."],
    )
