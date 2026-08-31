from collections.abc import Iterator
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from scholarlead_agent.agent.conversation import TaskContext
from scholarlead_agent.agent.loop import AgentRunResult, AgentToolExecution
from scholarlead_agent.agent.tool_types import ToolResult
from scholarlead_agent.api.app import create_app
from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.config import AppConfig
from scholarlead_agent.database import initialize_database
from scholarlead_agent.services.agent_result_persistence import persist_agent_run_result
from tests.test_agent_result_persistence import make_run_result


def make_client(db_path: Path) -> TestClient:
    app = create_app()

    def override_database() -> Iterator[sqlite3.Connection]:
        with initialize_database(db_path) as connection:
            yield connection

    app.dependency_overrides[get_database] = override_database
    return TestClient(app)


def test_api_agent_run_persists_leads_and_caches_idempotent_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "api.sqlite"
    client = make_client(db_path)
    source_result = make_run_result(tmp_path)
    calls: list[str] = []

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.load_config",
        lambda: AppConfig(agent_max_results_limit=5),
    )

    def fake_run_agent_conversation(message: str, **kwargs: object):
        calls.append(message)
        context = kwargs["context"]
        assert getattr(context, "max_results_limit") == 5
        result = AgentRunResult(
            final_answer="Found one PubMed lead.",
            messages=[
                {
                    "role": "tool",
                    "name": "search_pubmed",
                    "content": (
                        '{"success": true, "source": "pubmed", '
                        '"data": {"source": "pubmed", "task_id": '
                        '"pubmed-agent-test", "leads": [{"lead_id": "lead-1"}]}}'
                    ),
                }
            ],
            turns=2,
            tool_executions=[
                AgentToolExecution(
                    name="search_pubmed",
                    result=ToolResult(
                        success=True,
                        source="pubmed",
                        data={
                            "source": "pubmed",
                            "task_id": "pubmed-agent-test",
                            "leads": [{"lead_id": "lead-1"}],
                            "run_report_path": str(source_result.run_report_path),
                        },
                        persistence_payload=source_result,
                    ),
                )
            ],
        )
        context = TaskContext(
            conversation_id="conv-agent-test",
            task_id="pubmed-agent-test",
            last_lead_ids=["old-lead", "lead-1"],
        )
        return "conv-agent-test", result, context

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    payload = {
        "message": "Find one PubMed lead.",
        "max_turns": 3,
        "idempotency_key": "agent-click-1",
    }
    first = client.post("/api/agent/run", json=payload)
    second = client.post("/api/agent/run", json=payload)
    lead = client.get("/api/leads/lead-1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls == ["Find one PubMed lead."]
    data = first.json()["data"]
    assert data["conversation_id"] == "conv-agent-test"
    assert data["primary_task_id"] == "pubmed-agent-test"
    assert data["current_turn_lead_ids"] == ["lead-1"]
    assert data["selected_lead_ids"] == ["lead-1"]
    assert data["lead_selection_mode"] == "current_turn"
    assert data["context_lead_ids"] == ["old-lead", "lead-1"]
    assert data["result_summary"]["persisted_lead_count"] == 1
    assert data["result_summary"]["selected_lead_count"] == 1
    assert data["artifacts"][0]["name"] == "pubmed_run_report.json"
    assert second.json()["data"] == data
    assert lead.status_code == 200


def test_api_agent_uses_configured_max_results_limit(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path / "api.sqlite")
    received_limits: list[int | None] = []

    def fake_run_agent_conversation(message: str, **kwargs: object):
        context = kwargs["context"]
        received_limits.append(getattr(context, "max_results_limit"))
        return (
            "conv-config-test",
            AgentRunResult(final_answer="No tool needed.", messages=[], turns=1),
            TaskContext(conversation_id="conv-config-test"),
        )

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.load_config",
        lambda: AppConfig(agent_max_results_limit=17),
    )
    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    response = client.post("/api/agent/run", json={"message": "Explain the workflow."})

    assert response.status_code == 200
    assert received_limits == [17]


def test_api_agent_passes_default_max_results_limit_to_tool_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_client(tmp_path / "api.sqlite")
    received_limits: list[int | None] = []

    def fake_run_agent_conversation(message: str, **kwargs: object):
        received_limits.append(getattr(kwargs["context"], "max_results_limit"))
        return (
            "conv-default-config-test",
            AgentRunResult(final_answer="No tool needed.", messages=[], turns=1),
            TaskContext(conversation_id="conv-default-config-test"),
        )

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.load_config",
        lambda: AppConfig(),
    )
    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    response = client.post("/api/agent/run", json={"message": "Explain the workflow."})

    assert response.status_code == 200
    assert received_limits == [50]


def test_api_agent_rejects_empty_message_with_safe_error(tmp_path: Path) -> None:
    client = make_client(tmp_path / "api.sqlite")

    response = client.post("/api/agent/run", json={"message": "   "})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AGENT_REQUEST"


def test_api_agent_does_not_expose_model_configuration_error(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path / "api.sqlite")

    def fake_run_agent_conversation(*_: object, **__: object):
        raise RuntimeError("missing OPENAI_API_KEY=secret-value")

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    response = client.post("/api/agent/run", json={"message": "Find a lead."})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "AGENT_RUN_FAILED"
    assert "secret-value" not in body["error"]["message"]


def test_api_agent_rejects_idempotency_key_reused_for_different_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_client(tmp_path / "api.sqlite")

    def fake_run_agent_conversation(message: str, **_: object):
        result = AgentRunResult(final_answer="No tool needed.", messages=[], turns=1)
        return "conv-agent-test", result, TaskContext(conversation_id="conv-agent-test")

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    first = client.post(
        "/api/agent/run",
        json={"message": "First request.", "idempotency_key": "same-key"},
    )
    second = client.post(
        "/api/agent/run",
        json={"message": "Different request.", "idempotency_key": "same-key"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_api_agent_returns_structured_verified_email_selection_for_follow_up(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "api.sqlite"
    with initialize_database(db_path) as connection:
        for lead_id, email, status in [
            ("verified-lead", "pi@example.edu", "verified_from_pubmed_affiliation"),
            ("missing-lead", None, "missing"),
        ]:
            connection.execute(
                """
                INSERT INTO leads (
                    lead_id, pi_full_name, verified_email, email_status, payload_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, '{}', '2026-08-31T00:00:00Z', '2026-08-31T00:00:00Z')
                """,
                (lead_id, lead_id, email, status),
            )
        connection.commit()
    client = make_client(db_path)

    def fake_run_agent_conversation(message: str, **_: object):
        return (
            "conv-filter-test",
            AgentRunResult(final_answer="Only the verified Lead remains.", messages=[], turns=1),
            TaskContext(
                conversation_id="conv-filter-test",
                last_lead_ids=["verified-lead", "missing-lead"],
            ),
        )

    monkeypatch.setattr(
        "scholarlead_agent.api.routers.agent.run_agent_conversation",
        fake_run_agent_conversation,
    )

    response = client.post(
        "/api/agent/run",
        json={"message": "只保留有公开验证邮箱的线索。"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_turn_lead_ids"] == []
    assert data["selected_lead_ids"] == ["verified-lead"]
    assert data["lead_selection_mode"] == "verified_email_only"
