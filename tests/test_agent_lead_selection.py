from scholarlead_agent.agent.conversation import TaskContext
from scholarlead_agent.database import initialize_database
from scholarlead_agent.services.agent_lead_selection import select_agent_leads


def _insert_lead(connection, lead_id: str, email: str | None, status: str) -> None:
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


def test_select_agent_leads_filters_verified_email_from_conversation_context(tmp_path) -> None:
    with initialize_database(tmp_path / "agent.sqlite") as connection:
        _insert_lead(
            connection,
            "verified-lead",
            "pi@example.edu",
            "verified_from_pubmed_affiliation",
        )
        _insert_lead(connection, "missing-lead", None, "missing")
        context = TaskContext(
            conversation_id="conv-1",
            last_lead_ids=["verified-lead", "missing-lead"],
        )

        selection = select_agent_leads(
            connection,
            message="只保留有公开验证邮箱的线索。",
            current_turn_lead_ids=[],
            task_context=context,
        )

    assert selection.selection_mode == "verified_email_only"
    assert selection.selected_lead_ids == ["verified-lead"]


def test_select_agent_leads_uses_current_turn_for_new_search(tmp_path) -> None:
    with initialize_database(tmp_path / "agent.sqlite") as connection:
        selection = select_agent_leads(
            connection,
            message="Search PubMed leads.",
            current_turn_lead_ids=["lead-2", "lead-1", "lead-2"],
            task_context=TaskContext(conversation_id="conv-1"),
        )

    assert selection.selection_mode == "current_turn"
    assert selection.selected_lead_ids == ["lead-2", "lead-1"]
