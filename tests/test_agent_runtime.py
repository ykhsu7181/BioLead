import json
from typing import Any

from scholarlead_agent.agent.model import ModelReply
from scholarlead_agent.agent.runtime import (
    build_default_tool_registry,
    extract_run_report_paths,
    extract_tool_names,
    extract_tool_sources,
    run_agent_conversation,
    run_agent_task,
)
from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.agent.registry import ToolRegistry


class FakeModel:
    def __init__(self, replies: list[ModelReply]) -> None:
        self.replies = replies
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return self.replies.pop(0)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_fake_tool("search_pubmed", "pubmed"))
    return registry


def _fake_tool(name: str, source: str) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Fake {source} tool.",
        input_schema={
            "type": "object",
            "additionalProperties": True,
            "properties": {},
        },
        effect="external",
        handler=lambda arguments: ToolResult(
            success=True,
            source=source,
            data={
                "source": source,
                "task_id": f"{source}-agent-test",
                "queried_sources": [source],
                "run_report_path": f"data/processed/{source}/report.json",
                "arguments": arguments,
            },
        ),
    )


def multi_source_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_fake_tool("search_pubmed", "pubmed"))
    registry.register(_fake_tool("search_crossref", "crossref"))
    registry.register(_fake_tool("search_openalex", "openalex"))
    registry.register(_fake_tool("search_funding", "nih_reporter"))
    return registry


def tool_call(name: str = "search_pubmed", arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": f"call-{name}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments or {"query": "single-cell cancer"}),
        },
    }


def test_build_default_tool_registry_registers_search_pubmed() -> None:
    registry = build_default_tool_registry()

    assert "search_pubmed" in registry.snapshot()
    assert "search_crossref" in registry.snapshot()
    assert "search_openalex" in registry.snapshot()
    assert "search_funding" in registry.snapshot()
    assert "generate_email_draft" in registry.snapshot()
    assert "send_email" not in registry.snapshot()


def test_run_agent_task_triggers_search_pubmed_with_fake_model() -> None:
    model = FakeModel(
        [
            ModelReply(tool_calls=[tool_call()], finish_reason="tool_calls"),
            ModelReply(
                content=(
                    "Found one PubMed result. PMID 123. "
                    "Email evidence should be checked before outreach."
                )
            ),
        ]
    )

    result = run_agent_task(
        "Find single-cell cancer PubMed leads.",
        model=model,
        tool_registry=make_registry(),
    )

    assert result.final_answer.startswith("Found one PubMed result")
    assert extract_tool_names(result.messages) == ["search_pubmed"]
    assert extract_run_report_paths(result.messages) == [
        "data/processed/pubmed/report.json"
    ]
    assert extract_tool_sources(result.messages) == ["pubmed"]
    tool_messages = [message for message in result.messages if message["role"] == "tool"]
    assert tool_messages[0]["tool_call_id"] == "call-search_pubmed"


def test_run_agent_task_does_not_force_tool_for_general_question() -> None:
    model = FakeModel([ModelReply(content="ScholarLead Agent can explain its limits.")])

    result = run_agent_task(
        "What can you do?",
        model=model,
        tool_registry=make_registry(),
    )

    assert result.final_answer == "ScholarLead Agent can explain its limits."
    assert extract_tool_names(result.messages) == []


def test_run_agent_task_can_coordinate_multiple_data_source_tools() -> None:
    model = FakeModel(
        [
            ModelReply(
                tool_calls=[
                    tool_call(
                        "search_pubmed",
                        {
                            "query": "single-cell cancer",
                            "from_date": "2025-01-01",
                            "to_date": "2025-12-31",
                            "max_results": 5,
                        },
                    ),
                    tool_call(
                        "search_crossref",
                        {"title": "single-cell cancer", "max_results": 5},
                    ),
                    tool_call(
                        "search_openalex",
                        {
                            "query": "single-cell cancer",
                            "from_date": "2025-01-01",
                            "to_date": "2025-12-31",
                            "max_results": 5,
                        },
                    ),
                    tool_call(
                        "search_funding",
                        {
                            "keyword": "single-cell cancer",
                            "from_year": 2025,
                            "to_year": 2026,
                            "max_results": 5,
                        },
                    ),
                ],
                finish_reason="tool_calls",
            ),
            ModelReply(
                content=(
                    "Used PubMed, Crossref, OpenAlex, and NIH RePORTER. "
                    "Funding and outsourcing evidence still need review."
                )
            ),
        ]
    )

    result = run_agent_task(
        "Use multiple sources for single-cell cancer.",
        model=model,
        tool_registry=multi_source_registry(),
        max_turns=3,
    )

    assert extract_tool_names(result.messages) == [
        "search_pubmed",
        "search_crossref",
        "search_openalex",
        "search_funding",
    ]
    assert extract_tool_sources(result.messages) == [
        "pubmed",
        "crossref",
        "openalex",
        "nih_reporter",
    ]
    assert "NIH RePORTER" in result.final_answer


def test_run_agent_conversation_persists_and_reuses_context(tmp_path) -> None:
    first_model = FakeModel(
        [
            ModelReply(
                tool_calls=[
                    tool_call(
                        "search_pubmed",
                        {
                            "query": "single-cell cancer",
                            "from_date": "2025-01-01",
                            "to_date": "2025-12-31",
                            "max_results": 2,
                        },
                    )
                ],
                finish_reason="tool_calls",
            ),
            ModelReply(content="Found two leads."),
        ]
    )
    conversation_id, first_result, first_context = run_agent_conversation(
        "Find single-cell cancer leads.",
        model=first_model,
        tool_registry=make_registry(),
        database_path=str(tmp_path / "agent.sqlite"),
    )

    assert conversation_id.startswith("conv-")
    assert first_result.final_answer == "Found two leads."
    assert first_context.task_id == "pubmed-agent-test"
    assert first_context.last_run_report_path == "data/processed/pubmed/report.json"

    second_model = FakeModel([ModelReply(content="Using previous leads only.")])
    same_conversation_id, second_result, second_context = run_agent_conversation(
        "Only keep verified email leads.",
        conversation_id=conversation_id,
        model=second_model,
        tool_registry=make_registry(),
        database_path=str(tmp_path / "agent.sqlite"),
    )

    assert same_conversation_id == conversation_id
    assert second_result.final_answer == "Using previous leads only."
    assert second_context.task_id == first_context.task_id
    second_call_messages = second_model.calls[0]["messages"]
    assert any(
        "task_id: pubmed-agent-test" in message.get("content", "")
        for message in second_call_messages
        if message["role"] == "system"
    )
    assert any(
        message["role"] == "assistant" and message["content"] == "Found two leads."
        for message in second_call_messages
    )


def test_run_agent_conversation_keeps_new_conversations_separate(tmp_path) -> None:
    db_path = str(tmp_path / "agent.sqlite")
    first_model = FakeModel([ModelReply(content="First answer.")])
    first_conversation_id, _, _ = run_agent_conversation(
        "First conversation.",
        model=first_model,
        tool_registry=make_registry(),
        database_path=db_path,
    )

    second_model = FakeModel([ModelReply(content="Second answer.")])
    second_conversation_id, _, _ = run_agent_conversation(
        "Second conversation.",
        model=second_model,
        tool_registry=make_registry(),
        database_path=db_path,
    )

    assert first_conversation_id != second_conversation_id
    second_messages = second_model.calls[0]["messages"]
    assert all(message.get("content") != "First answer." for message in second_messages)
