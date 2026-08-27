from scholarlead_agent import database_main
from scholarlead_agent.database import DATABASE_SCHEMA_VERSION


def test_database_main_initializes_configured_database(tmp_path, capsys) -> None:
    db_path = tmp_path / "scholarlead.sqlite"

    exit_code = database_main.main(
        ["--database-path", str(db_path), "--show-tables"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert db_path.exists()
    assert "ScholarLead database initialized" in output
    assert f"Schema version: {DATABASE_SCHEMA_VERSION}" in output
    assert "tasks" in output
    assert "email_drafts" in output
