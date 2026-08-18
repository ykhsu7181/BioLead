from pathlib import Path

import pytest

from scholarlead_agent.pubmed_parser import (
    deduplicate_pubmed_papers,
    get_pubmed_paper_dedup_key,
    normalize_pubmed_doi,
    parse_pubmed_xml,
)
from scholarlead_agent.pubmed_models import PubMedPaper


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pubmed_efetch_response.xml"


def test_parse_pubmed_xml_extracts_core_paper_fields() -> None:
    raw_xml = FIXTURE_PATH.read_text(encoding="utf-8")

    papers = parse_pubmed_xml(
        raw_xml,
        raw_record_path=Path("data/raw/pubmed/sample_efetch.xml"),
    )

    assert len(papers) == 2
    paper = papers[0]
    assert paper.source == "pubmed"
    assert paper.pmid == "12345678"
    assert paper.doi == "10.1000/abc"
    assert paper.title == "Single-cell RNA sequencing in cancer biology"
    assert paper.abstract == (
        "Single-cell sequencing helps resolve tumor heterogeneity. "
        "We profiled cancer samples with single-cell RNA sequencing."
    )
    assert paper.journal == "Journal of Genome Biology"
    assert paper.publication_date == "2024-01-15"
    assert paper.publication_year == 2024
    assert paper.article_types == [
        "Journal Article",
        "Research Support, Non-U.S. Gov't",
    ]
    assert paper.mesh_terms == ["Neoplasms", "Single-Cell Analysis"]
    assert paper.keywords == ["single-cell RNA sequencing", "cancer"]
    assert paper.source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert paper.raw_record_path == "data\\raw\\pubmed\\sample_efetch.xml"


def test_parse_pubmed_xml_extracts_author_order_and_affiliations() -> None:
    raw_xml = FIXTURE_PATH.read_text(encoding="utf-8")

    paper = parse_pubmed_xml(raw_xml)[0]

    assert len(paper.authors) == 2
    first_author = paper.authors[0]
    last_author = paper.authors[1]

    assert first_author.full_name == "John Smith"
    assert first_author.last_name == "Smith"
    assert first_author.fore_name == "John"
    assert first_author.initials == "J"
    assert first_author.author_position == 1
    assert first_author.is_last_author is False
    assert first_author.affiliations == [
        "Department of Biology, Example University, Boston, MA, USA."
    ]

    assert last_author.full_name == "Alice Chen"
    assert last_author.author_position == 2
    assert last_author.is_last_author is True
    assert last_author.affiliations == [
        "Genome Center, Example Institute, Shanghai, China."
    ]

    assert paper.affiliations == [
        "Department of Biology, Example University, Boston, MA, USA.",
        "Genome Center, Example Institute, Shanghai, China.",
    ]


def test_parse_pubmed_xml_handles_missing_optional_fields() -> None:
    raw_xml = FIXTURE_PATH.read_text(encoding="utf-8")

    paper = parse_pubmed_xml(raw_xml)[1]

    assert paper.pmid == "87654321"
    assert paper.doi is None
    assert paper.title == "Genome assembly resources for crop research"
    assert paper.abstract == ""
    assert paper.journal == "Plant Genomics Reports"
    assert paper.publication_date == "2023"
    assert paper.publication_year == 2023
    assert paper.article_types == []
    assert paper.mesh_terms == []
    assert paper.keywords == []
    assert paper.authors[0].full_name == "Crop Genome Consortium"
    assert paper.authors[0].is_last_author is True
    assert paper.affiliations == []
    assert paper.source_url == "https://pubmed.ncbi.nlm.nih.gov/87654321/"


@pytest.mark.parametrize(
    ("raw_doi", "expected"),
    [
        ("https://doi.org/10.1000/ABC ", "10.1000/abc"),
        ("http://doi.org/10.1000/ABC", "10.1000/abc"),
        ("doi:10.1000/ABC", "10.1000/abc"),
        (" 10.1000/ABC ", "10.1000/abc"),
        (" ", None),
        (None, None),
    ],
)
def test_normalize_pubmed_doi(raw_doi: str | None, expected: str | None) -> None:
    assert normalize_pubmed_doi(raw_doi) == expected


def test_parse_pubmed_xml_rejects_malformed_xml() -> None:
    with pytest.raises(ValueError, match="PubMed XML is malformed"):
        parse_pubmed_xml("<PubmedArticleSet>")


def make_paper(
    *,
    pmid: str,
    doi: str | None,
    title: str = "A title",
) -> PubMedPaper:
    return PubMedPaper(
        source="pubmed",
        pmid=pmid,
        doi=doi,
        title=title,
        abstract="",
        journal="",
        publication_date="",
        publication_year=None,
        article_types=[],
        mesh_terms=[],
        keywords=[],
        authors=[],
        affiliations=[],
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    )


def test_get_pubmed_paper_dedup_key_prefers_doi_over_pmid() -> None:
    paper = make_paper(pmid="123", doi="HTTPS://DOI.ORG/10.1000/ABC")

    assert get_pubmed_paper_dedup_key(paper) == ("doi", "10.1000/abc")


def test_get_pubmed_paper_dedup_key_uses_pmid_when_doi_missing() -> None:
    paper = make_paper(pmid="123", doi=None)

    assert get_pubmed_paper_dedup_key(paper) == ("pmid", "123")


def test_deduplicate_pubmed_papers_removes_duplicate_doi_and_keeps_first() -> None:
    first = make_paper(pmid="123", doi="10.1000/abc", title="First")
    duplicate = make_paper(pmid="456", doi="https://doi.org/10.1000/ABC", title="Duplicate")

    result = deduplicate_pubmed_papers([first, duplicate])

    assert result == [first]


def test_deduplicate_pubmed_papers_uses_pmid_when_doi_missing() -> None:
    first = make_paper(pmid="123", doi=None, title="First")
    duplicate = make_paper(pmid="123", doi=None, title="Duplicate")

    result = deduplicate_pubmed_papers([first, duplicate])

    assert result == [first]


def test_deduplicate_pubmed_papers_does_not_merge_similar_titles_with_different_doi() -> None:
    first = make_paper(pmid="123", doi="10.1000/abc", title="Genome assembly study")
    second = make_paper(pmid="456", doi="10.1000/def", title="Genome assembly study")

    result = deduplicate_pubmed_papers([first, second])

    assert result == [first, second]


def test_deduplicate_pubmed_papers_keeps_records_without_doi_or_pmid() -> None:
    first = make_paper(pmid="", doi=None, title="Untitled")
    second = make_paper(pmid="", doi=None, title="Untitled")

    result = deduplicate_pubmed_papers([first, second])

    assert result == [first, second]
