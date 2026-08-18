"""Parse PubMed XML into structured paper records."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedPaper


MONTHS = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def parse_pubmed_xml(
    raw_xml: str,
    *,
    raw_record_path: Path | str | None = None,
) -> list[PubMedPaper]:
    """Parse a PubMed EFetch XML response into structured papers."""

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as error:
        raise ValueError("PubMed XML is malformed") from error

    return [
        _parse_pubmed_article(article, raw_record_path=raw_record_path)
        for article in root.findall(".//PubmedArticle")
    ]


def normalize_pubmed_doi(value: str | None) -> str | None:
    """Normalize DOI values found in PubMed XML."""

    if value is None:
        return None

    normalized = value.strip()
    lowered = normalized.lower()

    if lowered.startswith("https://doi.org/"):
        normalized = normalized[len("https://doi.org/") :]
    elif lowered.startswith("http://doi.org/"):
        normalized = normalized[len("http://doi.org/") :]
    elif lowered.startswith("doi:"):
        normalized = normalized[len("doi:") :]

    normalized = normalized.strip().lower()
    return normalized or None


def deduplicate_pubmed_papers(papers: list[PubMedPaper]) -> list[PubMedPaper]:
    """Deduplicate papers by DOI first, then PMID when DOI is missing."""

    seen_keys: set[tuple[str, str]] = set()
    results: list[PubMedPaper] = []

    for paper in papers:
        dedup_key = get_pubmed_paper_dedup_key(paper)
        if dedup_key is None:
            results.append(paper)
            continue

        if dedup_key in seen_keys:
            continue

        seen_keys.add(dedup_key)
        results.append(paper)

    return results


def get_pubmed_paper_dedup_key(paper: PubMedPaper) -> tuple[str, str] | None:
    """Return the deduplication key used for a PubMed paper."""

    doi = normalize_pubmed_doi(paper.doi)
    if doi:
        return ("doi", doi)

    pmid = paper.pmid.strip()
    if pmid:
        return ("pmid", pmid)

    return None


def _parse_pubmed_article(
    article: ET.Element,
    *,
    raw_record_path: Path | str | None,
) -> PubMedPaper:
    medline = article.find("MedlineCitation")
    article_node = medline.find("Article") if medline is not None else None

    pmid = _text(article, "./MedlineCitation/PMID")
    authors = _parse_authors(article_node)

    return PubMedPaper(
        source="pubmed",
        pmid=pmid,
        doi=_extract_doi(article),
        title=_normalize_whitespace(_text(article_node, "ArticleTitle")),
        abstract=_extract_abstract(article_node),
        journal=_normalize_whitespace(_text(article_node, "Journal/Title")),
        publication_date=_extract_publication_date(article_node),
        publication_year=_extract_publication_year(article_node),
        article_types=_extract_text_list(article_node, "PublicationTypeList/PublicationType"),
        mesh_terms=_extract_text_list(medline, "MeshHeadingList/MeshHeading/DescriptorName"),
        keywords=_extract_text_list(medline, "KeywordList/Keyword"),
        authors=authors,
        affiliations=_deduplicate(
            affiliation
            for author in authors
            for affiliation in author.affiliations
        ),
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        raw_record_path=str(raw_record_path) if raw_record_path is not None else None,
    )


def _extract_doi(article: ET.Element) -> str | None:
    for article_id in article.findall(".//ArticleId"):
        if article_id.attrib.get("IdType", "").lower() == "doi":
            doi = normalize_pubmed_doi(_element_text(article_id))
            if doi:
                return doi

    for elocation_id in article.findall(".//ELocationID"):
        if elocation_id.attrib.get("EIdType", "").lower() == "doi":
            doi = normalize_pubmed_doi(_element_text(elocation_id))
            if doi:
                return doi

    return None


def _extract_abstract(article_node: ET.Element | None) -> str:
    if article_node is None:
        return ""

    abstract_parts = [
        _normalize_whitespace(_element_text(abstract_text))
        for abstract_text in article_node.findall("Abstract/AbstractText")
    ]
    return " ".join(part for part in abstract_parts if part)


def _parse_authors(article_node: ET.Element | None) -> list[PubMedAuthor]:
    if article_node is None:
        return []

    author_nodes = article_node.findall("AuthorList/Author")
    authors: list[PubMedAuthor] = []
    last_position = len(author_nodes)

    for index, author_node in enumerate(author_nodes, start=1):
        last_name = _normalize_whitespace(_text(author_node, "LastName"))
        fore_name = _normalize_whitespace(_text(author_node, "ForeName"))
        initials = _normalize_whitespace(_text(author_node, "Initials"))
        collective_name = _normalize_whitespace(_text(author_node, "CollectiveName"))
        full_name = _build_full_name(
            last_name=last_name,
            fore_name=fore_name,
            collective_name=collective_name,
        )

        authors.append(
            PubMedAuthor(
                full_name=full_name,
                last_name=last_name,
                fore_name=fore_name,
                initials=initials,
                author_position=index,
                is_last_author=index == last_position,
                affiliations=_extract_text_list(
                    author_node,
                    "AffiliationInfo/Affiliation",
                ),
            )
        )

    return authors


def _build_full_name(
    *,
    last_name: str,
    fore_name: str,
    collective_name: str,
) -> str:
    if collective_name:
        return collective_name
    return " ".join(part for part in [fore_name, last_name] if part)


def _extract_publication_date(article_node: ET.Element | None) -> str:
    pub_date = (
        article_node.find("Journal/JournalIssue/PubDate")
        if article_node is not None
        else None
    )
    if pub_date is None:
        return ""

    year = _normalize_whitespace(_text(pub_date, "Year"))
    month = _normalize_month(_normalize_whitespace(_text(pub_date, "Month")))
    day = _normalize_day(_normalize_whitespace(_text(pub_date, "Day")))
    medline_date = _normalize_whitespace(_text(pub_date, "MedlineDate"))

    if year and month and day:
        return f"{year}-{month}-{day}"
    if year and month:
        return f"{year}-{month}"
    if year:
        return year
    return medline_date


def _extract_publication_year(article_node: ET.Element | None) -> int | None:
    pub_date = _extract_publication_date(article_node)
    if len(pub_date) >= 4 and pub_date[:4].isdigit():
        return int(pub_date[:4])
    return None


def _normalize_month(value: str) -> str:
    if not value:
        return ""
    if value.isdigit():
        return value.zfill(2)
    return MONTHS.get(value[:3].lower(), "")


def _normalize_day(value: str) -> str:
    if not value:
        return ""
    if value.isdigit():
        return value.zfill(2)
    return ""


def _extract_text_list(parent: ET.Element | None, path: str) -> list[str]:
    if parent is None:
        return []
    return _deduplicate(
        _normalize_whitespace(_element_text(element))
        for element in parent.findall(path)
    )


def _deduplicate(values: object) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = _normalize_whitespace(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _text(parent: ET.Element | None, path: str) -> str:
    if parent is None:
        return ""
    found = parent.find(path)
    if found is None:
        return ""
    return _element_text(found)


def _element_text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())
