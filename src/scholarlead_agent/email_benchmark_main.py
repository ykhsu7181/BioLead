"""Run the offline Email-E8 acceptance benchmark."""

from __future__ import annotations

import json

from scholarlead_agent.services.email_draft_benchmark import run_email_draft_benchmark


def main() -> None:
    result = run_email_draft_benchmark()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
