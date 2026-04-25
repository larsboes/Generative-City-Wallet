"""
SQLite connection helper for the Spark backend.
Uses a single file DB for the hackathon — swap for Postgres in prod.
"""

import sqlite3
from pathlib import Path

from spark.config import DB_PATH

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and row factory."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database(db_path: str | None = None) -> None:
    """Create all tables from schema.sql if they don't exist."""
    conn = get_connection(db_path)
    schema = _SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.close()
