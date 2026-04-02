"""Database connection manager for the IndieGameDrop dashboard."""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from flask import current_app


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Open a read-only SQLite connection as a context manager.

    Uses ``row_factory = sqlite3.Row`` so columns are accessible by name.
    If the database file is missing, yields a temporary in-memory database
    with no tables (queries will return empty results instead of crashing).

    Yields:
        sqlite3.Connection: A read-only database connection.
    """
    db_path: str = current_app.config.get("DB_PATH", "")
    if db_path and os.path.exists(db_path):
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
