"""Persist supported Agent Tool results through existing database helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from scholarlead_agent.agent.loop import AgentRunResult
from scholarlead_agent.database import persist_pubmed_run_result


@dataclass(frozen=True)
class AgentPersistenceResult:
    """Public-safe summary of records persisted from one Agent turn."""

    primary_task_id: str | None
    task_ids_by_source: dict[str, str]
    current_turn_lead_ids: list[str]
    artifacts: list[dict[str, str]]
    reported_lead_count: int
    persisted_lead_count: int


def persist_agent_run_result(
    connection: sqlite3.Connection,
    result: AgentRunResult,
) -> AgentPersistenceResult:
    """Persist supported internal Tool payloads before exposing Lead IDs."""

    task_ids_by_source: dict[str, str] = {}
    current_turn_lead_ids: list[str] = []
    artifacts: list[dict[str, str]] = []
    reported_lead_count = 0
    primary_task_id: str | None = None

    for execution in result.tool_executions:
        tool_result = execution.result
        if not tool_result.success:
            continue

        data = tool_result.data
        source = _string(data.get("source")) or tool_result.source
        task_id = _string(data.get("task_id"))
        if task_id and source not in task_ids_by_source:
            task_ids_by_source[source] = task_id
        artifacts.extend(_artifacts_from_data(source, data))
        reported_lead_count += _lead_count_from_data(data)

        if execution.name != "search_pubmed" or tool_result.persistence_payload is None:
            continue

        pubmed_result = tool_result.persistence_payload
        persist_pubmed_run_result(connection, pubmed_result)
        persisted_ids = _persisted_pubmed_lead_ids(connection, pubmed_result.task_id)
        current_turn_lead_ids.extend(
            lead_id for lead_id in persisted_ids if lead_id not in current_turn_lead_ids
        )
        primary_task_id = primary_task_id or str(pubmed_result.task_id)

    return AgentPersistenceResult(
        primary_task_id=primary_task_id,
        task_ids_by_source=task_ids_by_source,
        current_turn_lead_ids=current_turn_lead_ids,
        artifacts=_deduplicate_artifacts(artifacts),
        reported_lead_count=reported_lead_count,
        persisted_lead_count=len(current_turn_lead_ids),
    )


def _persisted_pubmed_lead_ids(
    connection: sqlite3.Connection,
    task_id: str,
) -> list[str]:
    rows = connection.execute(
        "SELECT lead_id FROM leads WHERE task_id = ? ORDER BY lead_id",
        (task_id,),
    ).fetchall()
    return [str(row["lead_id"]) for row in rows]


def _artifacts_from_data(source: str, data: dict[str, Any]) -> list[dict[str, str]]:
    path = _string(data.get("run_report_path"))
    if not path:
        return []
    name = Path(path).name
    if not name:
        return []
    return [{"source": source, "kind": "run_report", "name": name}]


def _lead_count_from_data(data: dict[str, Any]) -> int:
    leads = data.get("leads")
    return len(leads) if isinstance(leads, list) else 0


def _string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _deduplicate_artifacts(artifacts: list[dict[str, str]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact not in results:
            results.append(artifact)
    return results
