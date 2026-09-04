"""Database-backed query service for the product Lead library."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sqlite3
from typing import Any

from scholarlead_agent.services.lead_contact_status import (
    CONTACT_STATUSES,
    LEAD_CONTACT_RANKS_CTE,
    LEAD_CONTACT_STATUS_SQL,
)


LEAD_SCOPES = ("all", "current")
LEAD_PAGE_SIZES = (20, 50, 100)
LEAD_SORT_DIRECTIONS = ("asc", "desc")
EMAIL_DISPLAY_STATUSES = ("verified", "missing", "review_required")

SORT_COLUMNS = {
    "name": "l.pi_full_name",
    "institution": "l.institution",
    "country": "l.country",
    "email_status": "email_display_status",
    "contact_status": "contact_status",
    "last_seen_at": "last_seen_at",
}

_EMAIL_DISPLAY_STATUS_SQL = """
CASE
    WHEN LOWER(TRIM(COALESCE(l.email_status, ''))) LIKE 'verified_%'
        THEN 'verified'
    WHEN TRIM(COALESCE(l.email_status, '')) = ''
      OR LOWER(TRIM(COALESCE(l.email_status, ''))) = 'missing'
        THEN 'missing'
    ELSE 'review_required'
END
"""

_DISCOVERY_CTES = """
discovery_summary AS (
    SELECT
        lead_id,
        MIN(discovered_at) AS first_seen_at,
        MAX(discovered_at) AS last_seen_at,
        COUNT(*) AS discovery_count
    FROM lead_discoveries
    GROUP BY lead_id
),
latest_discovery AS (
    SELECT task_id, lead_id, source, discovered_at
    FROM (
        SELECT
            d.*,
            ROW_NUMBER() OVER (
                PARTITION BY d.lead_id
                ORDER BY d.discovered_at DESC, d.task_id DESC
            ) AS row_number
        FROM lead_discoveries AS d
    )
    WHERE row_number = 1
)
"""

_BASE_FROM_SQL = """
FROM leads AS l
LEFT JOIN discovery_summary AS discovery
    ON discovery.lead_id = l.lead_id
LEFT JOIN latest_discovery AS latest
    ON latest.lead_id = l.lead_id
LEFT JOIN tasks AS latest_task
    ON latest_task.task_id = latest.task_id
LEFT JOIN lead_contact_ranks AS contact_ranks
    ON contact_ranks.lead_id = l.lead_id
"""


@dataclass(frozen=True)
class LeadListQuery:
    page: int = 1
    page_size: int = 20
    scope: str = "all"
    task_id: str | None = None
    query: str | None = None
    country: str | None = None
    research: str | None = None
    email_status: str | None = None
    contact_status: str | None = None
    source: str | None = None
    manual_review: bool | None = None
    sort_by: str = "last_seen_at"
    sort_dir: str = "desc"
    lead_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LeadListResult:
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    scope_total: int
    all_total: int
    scope: str
    task_id: str | None
    sort_by: str
    sort_dir: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def query_leads(
    connection: sqlite3.Connection,
    query: LeadListQuery,
) -> LeadListResult:
    """Query Lead DTOs with stable scope, filtering, sorting, and pagination."""

    _validate_query(connection, query)
    ctes = f"WITH {LEAD_CONTACT_RANKS_CTE}, {_DISCOVERY_CTES}"
    scope_clauses, scope_parameters = _scope_clauses(query)
    filter_clauses, filter_parameters = _filter_clauses(query)
    scope_where = _where(scope_clauses)
    filtered_where = _where([*scope_clauses, *filter_clauses])

    all_total = _count(connection, "SELECT COUNT(*) FROM leads")
    scope_total = _count(
        connection,
        f"{ctes} SELECT COUNT(*) {_BASE_FROM_SQL} {scope_where}",
        scope_parameters,
    )
    total = _count(
        connection,
        f"{ctes} SELECT COUNT(*) {_BASE_FROM_SQL} {filtered_where}",
        [*scope_parameters, *filter_parameters],
    )

    current_task_id = query.task_id or ""
    sort_column = SORT_COLUMNS[query.sort_by]
    sort_direction = query.sort_dir.upper()
    offset = (query.page - 1) * query.page_size
    rows = connection.execute(
        f"""
        {ctes}
        SELECT
            l.*,
            {_EMAIL_DISPLAY_STATUS_SQL} AS email_display_status,
            {LEAD_CONTACT_STATUS_SQL} AS contact_status,
            COALESCE(discovery.first_seen_at, l.created_at) AS first_seen_at,
            COALESCE(discovery.last_seen_at, l.updated_at) AS last_seen_at,
            COALESCE(discovery.discovery_count, 0) AS discovery_count,
            latest.source AS latest_source,
            latest.task_id AS latest_task_id,
            latest_task.query AS latest_task_query,
            EXISTS (
                SELECT 1 FROM lead_discoveries AS current_discovery
                WHERE current_discovery.lead_id = l.lead_id
                  AND current_discovery.task_id = ?
            ) AS current_task_match
        {_BASE_FROM_SQL}
        {filtered_where}
        ORDER BY {sort_column} {sort_direction}, l.lead_id ASC
        LIMIT ? OFFSET ?
        """,
        (
            current_task_id,
            *scope_parameters,
            *filter_parameters,
            query.page_size,
            offset,
        ),
    ).fetchall()
    return LeadListResult(
        items=[_lead_list_item(dict(row), matched_source=query.source) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
        scope_total=scope_total,
        all_total=all_total,
        scope=query.scope,
        task_id=query.task_id,
        sort_by=query.sort_by,
        sort_dir=query.sort_dir,
    )


def fetch_lead_filter_options(connection: sqlite3.Connection) -> dict[str, list[str]]:
    """Return filter choices that are backed by persisted data."""

    countries = _single_column(
        connection,
        """
        SELECT DISTINCT TRIM(country) AS value
        FROM leads
        WHERE TRIM(COALESCE(country, '')) <> ''
        ORDER BY value COLLATE NOCASE
        """,
    )
    sources = _single_column(
        connection,
        """
        SELECT DISTINCT TRIM(source) AS value
        FROM lead_discoveries
        WHERE TRIM(COALESCE(source, '')) <> ''
        ORDER BY value COLLATE NOCASE
        """,
    )
    research_topics = _single_column(
        connection,
        """
        SELECT DISTINCT TRIM(CAST(topic.value AS TEXT)) AS value
        FROM leads AS l
        JOIN json_each(
            CASE
                WHEN json_valid(l.payload_json)
                 AND json_type(l.payload_json, '$.research_topics') = 'array'
                    THEN json_extract(l.payload_json, '$.research_topics')
                WHEN json_valid(l.payload_json)
                 AND json_type(l.payload_json, '$.matched_keywords') = 'array'
                    THEN json_extract(l.payload_json, '$.matched_keywords')
                ELSE '[]'
            END
        ) AS topic
        WHERE TRIM(CAST(topic.value AS TEXT)) <> ''
        ORDER BY value COLLATE NOCASE
        """,
    )
    return {
        "countries": countries,
        "research_topics": research_topics,
        "sources": sources,
        "email_statuses": list(EMAIL_DISPLAY_STATUSES),
        "contact_statuses": list(CONTACT_STATUSES),
    }


def _validate_query(connection: sqlite3.Connection, query: LeadListQuery) -> None:
    if isinstance(query.page, bool) or query.page < 1:
        raise ValueError("page must be at least 1")
    if query.page_size not in LEAD_PAGE_SIZES:
        raise ValueError("page_size must be one of 20, 50, or 100")
    if query.scope not in LEAD_SCOPES:
        raise ValueError("scope must be all or current")
    if query.sort_by not in SORT_COLUMNS:
        raise ValueError("unsupported sort_by")
    if query.sort_dir not in LEAD_SORT_DIRECTIONS:
        raise ValueError("sort_dir must be asc or desc")
    if query.email_status and query.email_status not in EMAIL_DISPLAY_STATUSES:
        raise ValueError("unsupported email_status")
    if query.contact_status and query.contact_status not in CONTACT_STATUSES:
        raise ValueError("unsupported contact_status")
    if query.scope == "current":
        if not query.task_id:
            raise ValueError("task_id is required when scope=current")
        task_exists = connection.execute(
            "SELECT 1 FROM tasks WHERE task_id = ?",
            (query.task_id,),
        ).fetchone()
        if task_exists is None:
            raise ValueError("task_id does not identify a persisted task")


def _scope_clauses(query: LeadListQuery) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if query.scope == "current":
        clauses.append(
            """
            EXISTS (
                SELECT 1 FROM lead_discoveries AS scoped_discovery
                WHERE scoped_discovery.lead_id = l.lead_id
                  AND scoped_discovery.task_id = ?
            )
            """
        )
        parameters.append(query.task_id)
    return clauses, parameters


def _filter_clauses(query: LeadListQuery) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if query.lead_ids:
        placeholders = ", ".join("?" for _ in query.lead_ids)
        clauses.append(f"l.lead_id IN ({placeholders})")
        parameters.extend(query.lead_ids)
    if query.query:
        pattern = f"%{_escape_like(query.query.strip())}%"
        clauses.append(
            """
            (
                l.pi_full_name LIKE ? ESCAPE '\\'
                OR COALESCE(l.institution, '') LIKE ? ESCAPE '\\'
                OR COALESCE(l.verified_email, '') LIKE ? ESCAPE '\\'
                OR COALESCE(l.country, '') LIKE ? ESCAPE '\\'
            )
            """
        )
        parameters.extend([pattern] * 4)
    if query.country:
        clauses.append("LOWER(TRIM(COALESCE(l.country, ''))) = LOWER(TRIM(?))")
        parameters.append(query.country)
    if query.research:
        clauses.append(_research_filter_sql())
        parameters.extend([query.research, query.research])
    if query.email_status:
        clauses.append(f"({_EMAIL_DISPLAY_STATUS_SQL}) = ?")
        parameters.append(query.email_status)
    if query.contact_status:
        clauses.append(f"({LEAD_CONTACT_STATUS_SQL}) = ?")
        parameters.append(query.contact_status)
    if query.source:
        source_task_clause = "AND source_discovery.task_id = ?" if query.scope == "current" else ""
        clauses.append(
            f"""
            EXISTS (
                SELECT 1 FROM lead_discoveries AS source_discovery
                WHERE source_discovery.lead_id = l.lead_id
                  AND LOWER(source_discovery.source) = LOWER(?)
                  {source_task_clause}
            )
            """
        )
        parameters.append(query.source)
        if query.scope == "current":
            parameters.append(query.task_id)
    if query.manual_review is not None:
        clauses.append("l.manual_review_required = ?")
        parameters.append(int(query.manual_review))
    return clauses, parameters


def _research_filter_sql() -> str:
    return """
    (
        EXISTS (
            SELECT 1
            FROM json_each(
                CASE
                    WHEN json_valid(l.payload_json)
                     AND json_type(l.payload_json, '$.research_topics') = 'array'
                        THEN json_extract(l.payload_json, '$.research_topics')
                    ELSE '[]'
                END
            ) AS research_topic
            WHERE LOWER(TRIM(CAST(research_topic.value AS TEXT))) = LOWER(TRIM(?))
        )
        OR EXISTS (
            SELECT 1
            FROM json_each(
                CASE
                    WHEN json_valid(l.payload_json)
                     AND json_type(l.payload_json, '$.matched_keywords') = 'array'
                        THEN json_extract(l.payload_json, '$.matched_keywords')
                    ELSE '[]'
                END
            ) AS matched_keyword
            WHERE LOWER(TRIM(CAST(matched_keyword.value AS TEXT))) = LOWER(TRIM(?))
        )
    )
    """


def _lead_list_item(row: dict[str, Any], *, matched_source: str | None) -> dict[str, Any]:
    payload = _safe_json_object(row.pop("payload_json", "{}"))
    topics = _string_list(payload.get("research_topics"))
    if not topics:
        topics = _string_list(payload.get("matched_keywords"))
    return {
        "lead_id": str(row["lead_id"]),
        "pi_full_name": str(row["pi_full_name"]),
        "institution": row.get("institution"),
        "country": row.get("country") or "unknown",
        "country_code": payload.get("country_code"),
        "verified_email": row.get("verified_email"),
        "email_status": row.get("email_status") or "missing",
        "email_display_status": str(row["email_display_status"]),
        "contact_status": str(row["contact_status"]),
        "research_topics": topics,
        "manual_review_required": bool(row.get("manual_review_required")),
        "lead_score": row.get("lead_score"),
        "priority": row.get("priority"),
        "data_quality": row.get("data_quality"),
        "current_task_match": bool(row.get("current_task_match")),
        "first_seen_at": row.get("first_seen_at"),
        "last_seen_at": row.get("last_seen_at"),
        "discovery_count": int(row.get("discovery_count") or 0),
        "latest_source": row.get("latest_source"),
        "matched_source": matched_source,
        "latest_task_id": row.get("latest_task_id"),
        "latest_task_query": row.get("latest_task_query"),
        "recent_publication_title": payload.get("recent_publication_title"),
        "pmid": row.get("pmid"),
        "doi": row.get("doi"),
        "source_links": _string_list(payload.get("source_links")),
    }


def _safe_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        normalized = str(item).strip() if item is not None else ""
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _where(clauses: list[str]) -> str:
    return f"WHERE {' AND '.join(f'({clause})' for clause in clauses)}" if clauses else ""


def _count(
    connection: sqlite3.Connection,
    sql: str,
    parameters: list[Any] | None = None,
) -> int:
    row = connection.execute(sql, tuple(parameters or [])).fetchone()
    return int(row[0] if row is not None else 0)


def _single_column(connection: sqlite3.Connection, sql: str) -> list[str]:
    return [str(row["value"]) for row in connection.execute(sql).fetchall()]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
