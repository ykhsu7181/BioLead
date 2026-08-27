"""CLI entry point for ScholarLead Agent natural-language tasks."""

from __future__ import annotations

import argparse
from typing import Sequence

from scholarlead_agent.adapters.openai_compatible_chat import LLMAdapterError
from scholarlead_agent.agent.loop import AgentRunError
from scholarlead_agent.agent.runtime import (
    extract_run_report_paths,
    extract_tool_names,
    run_agent_task,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a ScholarLead Agent natural-language task."
    )
    parser.add_argument("task", nargs="+", help="Natural-language task text.")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=6,
        help="Maximum Agent Loop turns.",
    )
    parser.add_argument(
        "--show-messages",
        action="store_true",
        help="Print the full normalized message trace.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    task = " ".join(args.task).strip()

    try:
        result = run_agent_task(task, max_turns=args.max_turns)
    except (AgentRunError, LLMAdapterError, ValueError) as error:
        print(f"ScholarLead Agent run failed: {error}")
        return 1

    print("ScholarLead Agent run completed")
    print(f"Turns: {result.turns}")
    tools = extract_tool_names(result.messages)
    print(f"Tools used: {', '.join(tools) if tools else 'none'}")
    report_paths = extract_run_report_paths(result.messages)
    if report_paths:
        print(f"Run reports: {', '.join(report_paths)}")
    print("Final answer:")
    print(result.final_answer)

    if args.show_messages:
        print("Messages:")
        for message in result.messages:
            print(message)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
