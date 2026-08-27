from scholarlead_agent.data_source_adapter import (
    example_data_source_adapter_spec,
    forbidden_bypasses,
    required_run_report_fields,
    required_source_metadata_fields,
    validate_data_source_adapter_spec,
)


def test_example_data_source_adapter_spec_passes_stage38_contract() -> None:
    spec = example_data_source_adapter_spec("europe_pmc")

    result = validate_data_source_adapter_spec(spec)

    assert result.valid is True
    assert result.blockers == []
    assert spec.raw_storage_dir == "data/raw/europe_pmc"
    assert "EvidenceRecord" in spec.allowed_output_models


def test_adapter_spec_blocks_missing_raw_storage_and_evidence_output() -> None:
    spec = example_data_source_adapter_spec("bad_source")
    broken = spec.__class__(
        **{
            **spec.to_dict(),
            "raw_storage_dir": "",
            "allowed_output_models": ["UnifiedPaper"],
        }
    )

    result = validate_data_source_adapter_spec(broken)

    assert result.valid is False
    assert "raw_storage" in result.missing_components
    assert "adapter_must_output_evidence_records" in result.blockers


def test_adapter_spec_requires_source_metadata_and_run_report_fields() -> None:
    spec = example_data_source_adapter_spec("semantic_scholar")
    broken = spec.__class__(
        **{
            **spec.to_dict(),
            "source_metadata_fields": ["source_name"],
            "run_report_fields": ["task_id"],
        }
    )

    result = validate_data_source_adapter_spec(broken)

    assert result.valid is False
    assert "raw_file_path" in result.missing_metadata_fields
    assert "raw_files" in result.missing_run_report_fields
    assert "missing_required_source_metadata" in result.blockers


def test_stage38_forbidden_bypasses_are_documented() -> None:
    rules = forbidden_bypasses()

    assert "fastapi_route_direct_external_api" in rules
    assert "skip_raw_storage" in rules
    assert "llm_guess_missing_email" in rules
    assert "source_metadata" in required_run_report_fields()
    assert "license_or_terms_note" in required_source_metadata_fields()
