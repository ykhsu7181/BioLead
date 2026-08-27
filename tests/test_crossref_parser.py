from scholarlead_agent.crossref_parser import (
    deduplicate_crossref_works,
    parse_crossref_works,
)


def sample_item(**overrides):
    item = {
        "DOI": "10.1038/ABC123",
        "title": ["CRISPR imaging in cancer"],
        "abstract": "<jats:p>Abstract text.</jats:p>",
        "container-title": ["Nature"],
        "publisher": "Springer Nature",
        "published-print": {"date-parts": [[2024, 5, 2]]},
        "published-online": {"date-parts": [[2023, 12, 1]]},
        "author": [
            {"given": "Lei S", "family": "Qi"},
            {"name": "Genome Consortium"},
        ],
        "funder": [{"name": "National Institutes of Health"}],
        "reference-count": 12,
        "is-referenced-by-count": 34,
        "URL": "https://doi.org/10.1038/ABC123",
    }
    item.update(overrides)
    return item


def test_parse_crossref_single_doi_response() -> None:
    works = parse_crossref_works(
        {"message": sample_item()},
        raw_record_path="raw/crossref.json",
    )

    assert len(works) == 1
    work = works[0]
    assert work.source == "crossref"
    assert work.crossref_id == "10.1038/abc123"
    assert work.doi == "10.1038/abc123"
    assert work.title == "CRISPR imaging in cancer"
    assert work.abstract == "Abstract text."
    assert work.journal == "Nature"
    assert work.publisher == "Springer Nature"
    assert work.publication_date == "2024-05-02"
    assert work.publication_year == 2024
    assert work.authors == ["Lei S Qi", "Genome Consortium"]
    assert work.funder_names == ["National Institutes of Health"]
    assert work.reference_count == 12
    assert work.is_referenced_by_count == 34
    assert work.raw_record_path == "raw/crossref.json"


def test_parse_crossref_title_response_items_and_date_fallback() -> None:
    works = parse_crossref_works(
        {
            "message": {
                "items": [
                    sample_item(
                        DOI=None,
                        **{
                            "published-print": None,
                            "published-online": {"date-parts": [[2023, 7]]},
                        },
                    )
                ]
            }
        }
    )

    assert len(works) == 1
    assert works[0].doi is None
    assert works[0].publication_date == "2023-07"
    assert works[0].publication_year == 2023


def test_parse_crossref_empty_or_malformed_response_returns_empty_list() -> None:
    assert parse_crossref_works({}) == []
    assert parse_crossref_works({"message": {"items": "bad"}}) == []


def test_deduplicate_crossref_works_prefers_doi_then_weak_key() -> None:
    first, duplicate_doi, weak, duplicate_weak = parse_crossref_works(
        {
            "message": {
                "items": [
                    sample_item(DOI="10.1/ABC", title=["First"]),
                    sample_item(DOI="https://doi.org/10.1/abc", title=["Duplicate"]),
                    sample_item(DOI=None, title=["Same Title"], author=[{"family": "Smith"}]),
                    sample_item(DOI=None, title=[" same  title "], author=[{"family": "Smith"}]),
                ]
            }
        }
    )

    deduped = deduplicate_crossref_works(
        [first, duplicate_doi, weak, duplicate_weak]
    )

    assert [work.title for work in deduped] == ["First", "Same Title"]
