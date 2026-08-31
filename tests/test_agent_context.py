import json

from scholarlead_agent.agent.context import (
    build_context_messages,
    build_task_context_summary,
    task_context_from_agent_messages,
)
from scholarlead_agent.agent.conversation import (
    ConversationMessage,
    TaskContext,
    with_selected_lead_ids,
)


def test_build_context_messages_limits_recent_messages() -> None:
    task_context = TaskContext(
        conversation_id="conv-1",
        task_id="task-1",
        last_run_report_path="report.json",
        last_lead_ids=["lead-1", "lead-2"],
        last_selected_lead_ids=["lead-1"],
        updated_at="2026-08-26T10:00:00Z",
    )
    recent = [
        ConversationMessage(
            message_id=f"msg-{index}",
            conversation_id="conv-1",
            role="user" if index % 2 == 0 else "assistant",
            content=f"message {index}",
            created_at=f"2026-08-26T10:00:0{index}Z",
        )
        for index in range(4)
    ]

    messages = build_context_messages(
        task_context=task_context,
        recent_messages=recent,
        limit=2,
    )

    assert messages[0]["role"] == "system"
    assert "last_lead_ids: lead-1, lead-2" in messages[0]["content"]
    assert [message["content"] for message in messages[1:]] == ["message 2", "message 3"]


def test_task_context_from_agent_messages_extracts_tool_result_state() -> None:
    tool_payload = {
        "success": True,
        "source": "pubmed",
        "data": {
            "task_id": "task-pubmed-1",
            "run_report_path": "data/processed/pubmed/report.json",
            "leads": [{"lead_id": "lead-1"}, {"lead_id": "lead-2"}],
        },
    }
    previous = TaskContext(
        conversation_id="conv-1",
        task_id="old-task",
        last_run_report_path="old-report.json",
        last_lead_ids=["lead-0"],
        last_selected_lead_ids=["lead-0"],
        updated_at="2026-08-26T09:00:00Z",
    )

    context = task_context_from_agent_messages(
        conversation_id="conv-1",
        messages=[
            {
                "role": "tool",
                "name": "search_pubmed",
                "content": json.dumps(tool_payload),
            }
        ],
        previous=previous,
    )

    assert context.task_id == "task-pubmed-1"
    assert context.last_run_report_path == "data/processed/pubmed/report.json"
    assert context.last_lead_ids == ["lead-0", "lead-1", "lead-2"]
    assert context.last_selected_lead_ids == ["lead-0"]


def test_build_task_context_summary_handles_missing_context() -> None:
    assert build_task_context_summary(None) == "No previous task context is available."


def test_with_selected_lead_ids_preserves_task_context() -> None:
    original = TaskContext(
        conversation_id="conv-1",
        task_id="task-1",
        last_lead_ids=["lead-1", "lead-2"],
    )

    updated = with_selected_lead_ids(original, ["lead-2"])

    assert updated.conversation_id == "conv-1"
    assert updated.task_id == "task-1"
    assert updated.last_lead_ids == ["lead-1", "lead-2"]
    assert updated.last_selected_lead_ids == ["lead-2"]
