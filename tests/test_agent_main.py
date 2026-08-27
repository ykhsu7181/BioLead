from types import SimpleNamespace

from scholarlead_agent import agent_main


def test_agent_main_prints_summary(monkeypatch, capsys) -> None:
    def fake_run_agent_task(task: str, *, max_turns: int):
        assert task == "find pubmed leads"
        assert max_turns == 3
        return SimpleNamespace(
            final_answer="Final PubMed answer.",
            turns=2,
            messages=[
                {
                    "role": "tool",
                    "name": "search_pubmed",
                    "content": (
                        '{"success": true, "source": "pubmed", '
                        '"data": {"run_report_path": "report.json"}}'
                    ),
                }
            ],
        )

    monkeypatch.setattr(agent_main, "run_agent_task", fake_run_agent_task)

    exit_code = agent_main.main(["find", "pubmed", "leads", "--max-turns", "3"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ScholarLead Agent run completed" in output
    assert "Tools used: search_pubmed" in output
    assert "Run reports: report.json" in output
    assert "Final PubMed answer." in output


def test_agent_main_returns_error_code(monkeypatch, capsys) -> None:
    def fake_run_agent_task(task: str, *, max_turns: int):
        raise ValueError("missing config")

    monkeypatch.setattr(agent_main, "run_agent_task", fake_run_agent_task)

    exit_code = agent_main.main(["find", "pubmed", "leads"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "ScholarLead Agent run failed: missing config" in output
