from pathlib import Path

from scholarlead_agent.database import (
    fetch_all,
    fetch_task_paper_ids,
    initialize_database,
    insert_pubmed_paper,
    insert_task,
)
from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedPaper


def make_paper() -> PubMedPaper:
    author = PubMedAuthor(
        full_name="Lei S Qi",
        last_name="Qi",
        fore_name="Lei S",
        initials="LSQ",
        author_position=1,
        is_last_author=True,
        affiliations=["Stanford University, CA, USA. slqi@stanford.edu."],
    )
    return PubMedPaper(
        source="pubmed",
        pmid="41951915",
        doi="10.1000/example",
        title="CRISPR imaging",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_date="2026-08-01",
        publication_year=2026,
        article_types=["Journal Article"],
        mesh_terms=["Genome"],
        keywords=["CRISPR"],
        authors=[author],
        affiliations=author.affiliations,
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        raw_record_path="data/raw/pubmed/example.xml",
    )


def insert_test_task(connection, task_id: str) -> None:
    insert_task(
        connection,
        task_id=task_id,
        task_type="pubmed_search",
        status="success",
    )


def test_paper_discovery_preserves_multiple_tasks(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "db.sqlite") as connection:
        insert_test_task(connection, "task-a")
        insert_test_task(connection, "task-b")
        insert_pubmed_paper(
            connection,
            make_paper(),
            task_id="task-a",
            discovered_at="2026-09-01T10:00:00",
        )
        insert_pubmed_paper(
            connection,
            make_paper(),
            task_id="task-b",
            discovered_at="2026-09-02T10:00:00",
        )

        assert fetch_task_paper_ids(connection, "task-a") == ["pubmed:41951915"]
        assert fetch_task_paper_ids(connection, "task-b") == ["pubmed:41951915"]
        rows = fetch_all(
            connection,
            "SELECT task_id FROM paper_discoveries ORDER BY task_id",
        )

    assert rows == [{"task_id": "task-a"}, {"task_id": "task-b"}]


def test_same_task_paper_retry_is_idempotent(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "db.sqlite") as connection:
        insert_test_task(connection, "task-a")
        insert_pubmed_paper(connection, make_paper(), task_id="task-a")
        insert_pubmed_paper(connection, make_paper(), task_id="task-a")
        rows = fetch_all(connection, "SELECT * FROM paper_discoveries")

    assert len(rows) == 1
    assert rows[0]["source"] == "pubmed"
    assert rows[0]["source_record_id"] == "41951915"


def test_v5_paper_pointer_is_backfilled(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite"
    with initialize_database(db_path) as connection:
        insert_test_task(connection, "legacy-task")
        insert_pubmed_paper(connection, make_paper(), task_id="legacy-task")
        connection.execute("DROP TABLE paper_discoveries")
        connection.execute("DELETE FROM schema_migrations WHERE version = 6")
        connection.execute("PRAGMA user_version = 5")
        connection.commit()

    with initialize_database(db_path) as connection:
        rows = fetch_all(connection, "SELECT * FROM paper_discoveries")

    assert len(rows) == 1
    assert rows[0]["task_id"] == "legacy-task"
    assert rows[0]["source"] == "legacy"
