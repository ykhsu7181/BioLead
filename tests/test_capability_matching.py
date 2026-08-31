from scholarlead_agent.capability_matching import (
    CAPABILITY_MATCH_STATUS_MATCHED,
    CAPABILITY_MATCH_STATUS_NO_MATCH,
    CAPABILITY_MATCH_STATUS_PARTIAL,
    CapabilityMatchInput,
    capability_match_input_from_lead,
    capability_match_result_to_dict,
    match_sender_capabilities,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_capabilities import (
    SenderCapability,
    SenderCapabilityCatalog,
    SenderCapabilitySelectionPolicy,
)


def make_catalog(*capabilities: SenderCapability, max_count: int = 6) -> SenderCapabilityCatalog:
    return SenderCapabilityCatalog(
        profile_version="capabilities-v1",
        purpose="Test catalog",
        selection_policy=SenderCapabilitySelectionPolicy(
            target_candidate_count=4,
            max_candidate_count=max_count,
            min_candidate_count=0,
            allow_fewer_when_evidence_is_insufficient=True,
            zero_match_strategy="paper_only",
            llm_may_create_new_capabilities=False,
        ),
        capabilities=list(capabilities),
        source_policy={"intended_use": "test"},
        source_path="test.json",
    )


def make_capability(capability_id: str, term: str, *, enabled: bool = True) -> SenderCapability:
    return SenderCapability(
        capability_id=capability_id,
        capability_name=capability_id.replace("_", " ").title(),
        category="Test",
        description="Test capability",
        positive_keywords=[term],
        synonyms=[f"{term} synonym"],
        research_fields=[f"{term} field"],
        scientific_questions=[f"How does {term} work?"],
        methods=[f"{term} method"],
        enabled=enabled,
    )


def make_lead(**overrides: object) -> PubMedLead:
    values: dict[str, object] = {
        "lead_id": "lead-1",
        "pi_full_name": "Alex Example",
        "verified_email": "missing",
        "email_status": "missing",
        "email_source_url": "",
        "email_source_type": "",
        "name_email_match_confidence": "missing",
        "institution": "Example University",
        "country": "United States",
        "country_confidence": "high",
        "recent_publication_title": "Single-cell RNA sequencing in cancer",
        "abstract": "A study of tumor cell heterogeneity.",
        "journal": "Example Journal",
        "publication_year": 2026,
        "pmid": "123",
        "doi": None,
        "author_role": "candidate",
        "source_links": ["https://pubmed.ncbi.nlm.nih.gov/123/"],
        "data_quality": "missing_email_candidate",
        "manual_review_required": True,
        "notes": "",
        "matched_keywords": ["single-cell", "cancer"],
        "target_service_type": "internal-service-tag",
    }
    values.update(overrides)
    return PubMedLead(**values)


def test_match_sender_capabilities_returns_up_to_six_ranked_matches() -> None:
    catalog = make_catalog(
        *(make_capability(f"capability_{index}", f"term{index}") for index in range(7))
    )
    result = match_sender_capabilities(
        CapabilityMatchInput(abstract="term0 term1 term2 term3 term4 term5 term6"),
        catalog,
    )

    assert result.status == CAPABILITY_MATCH_STATUS_MATCHED
    assert len(result.items) == 6
    assert [item.capability_id for item in result.items] == [
        "capability_0",
        "capability_1",
        "capability_2",
        "capability_3",
        "capability_4",
        "capability_5",
    ]
    assert all(item.match_score >= 0.24 for item in result.items)
    assert result.capability_match_id.startswith("capability-match-")


def test_match_sender_capabilities_allows_partial_match_without_padding() -> None:
    catalog = make_catalog(
        make_capability("single_cell", "single-cell RNA-seq"),
        make_capability("spatial", "spatial transcriptomics"),
        make_capability("unrelated", "long-read sequencing"),
    )

    result = match_sender_capabilities(
        CapabilityMatchInput(
            paper_title="Single-cell RNA-seq and spatial transcriptomics",
        ),
        catalog,
    )

    assert result.status == CAPABILITY_MATCH_STATUS_PARTIAL
    assert [item.capability_id for item in result.items] == ["single_cell", "spatial"]


def test_match_sender_capabilities_returns_no_match_when_evidence_is_insufficient() -> None:
    result = match_sender_capabilities(
        CapabilityMatchInput(paper_title="Protein crystallography"),
        make_catalog(make_capability("single_cell", "single-cell RNA-seq")),
    )

    assert result.status == CAPABILITY_MATCH_STATUS_NO_MATCH
    assert result.items == []


def test_match_sender_capabilities_ignores_disabled_capabilities() -> None:
    result = match_sender_capabilities(
        CapabilityMatchInput(paper_title="Single-cell RNA-seq"),
        make_catalog(make_capability("single_cell", "single-cell RNA-seq", enabled=False)),
    )

    assert result.status == CAPABILITY_MATCH_STATUS_NO_MATCH
    assert result.items == []


def test_match_result_is_deterministic_and_export_ready() -> None:
    catalog = make_catalog(make_capability("single_cell", "single-cell RNA-seq"))
    match_input = CapabilityMatchInput(
        lead_id="lead-1",
        paper_title="Single-cell RNA-seq",
    )

    first = match_sender_capabilities(match_input, catalog)
    second = match_sender_capabilities(match_input, catalog)
    data = capability_match_result_to_dict(first)

    assert first == second
    assert data["lead_id"] == "lead-1"
    assert data["profile_version"] == "capabilities-v1"
    assert data["items"][0]["matched_terms"] == ["single-cell RNA-seq"]


def test_capability_match_input_from_lead_does_not_reuse_internal_service_tag() -> None:
    match_input = capability_match_input_from_lead(make_lead())

    assert match_input.lead_id == "lead-1"
    assert match_input.paper_title == "Single-cell RNA sequencing in cancer"
    assert match_input.keywords == ["single-cell", "cancer"]
    assert match_input.research_direction is None
