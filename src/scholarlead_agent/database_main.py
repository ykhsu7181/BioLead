"""CLI for initializing the ScholarLead Agent SQLite database."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from scholarlead_agent.config import load_config
from scholarlead_agent.database import (
    get_schema_version,
    initialize_database,
    list_tables,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the database CLI parser."""

    parser = argparse.ArgumentParser(
        description="Initialize the ScholarLead Agent SQLite database."
    )
    parser.add_argument(
        "--database-path",
        default=None,
        help="SQLite database path. Defaults to DATABASE_PATH or AppConfig.",
    )
    parser.add_argument(
        "--show-tables",
        action="store_true",
        help="Print initialized table names.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Initialize the configured SQLite database."""

    parser = build_parser()
    args = parser.parse_args(argv)
    path = Path(args.database_path) if args.database_path else load_config().database_path

    with initialize_database(path) as connection:
        version = get_schema_version(connection)
        tables = sorted(list_tables(connection))

    print("ScholarLead database initialized")
    print(f"Database: {path}")
    print(f"Schema version: {version}")
    if args.show_tables:
        print(f"Tables: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
