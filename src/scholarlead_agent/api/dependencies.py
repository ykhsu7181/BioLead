"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator
import sqlite3

from scholarlead_agent.config import load_config
from scholarlead_agent.database import initialize_database


def get_database() -> Iterator[sqlite3.Connection]:
    """Yield one initialized SQLite connection."""

    config = load_config()
    with initialize_database(config.database_path) as connection:
        yield connection
