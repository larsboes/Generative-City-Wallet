"""
SQLite connection/bootstrap helpers for the Spark backend.

Persistence operations should live in repository modules under `spark.repositories`.
Compatibility wrappers remain here for older call sites.
"""

import sqlite3
from pathlib import Path
from typing import Any

from spark.config import DB_PATH

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_SHARED_MEMORY_KEEPALIVE: sqlite3.Connection | None = None


def _normalize_sqlite_target(db_path: str) -> tuple[str, bool]:
    """Return (target, uri) for sqlite3.connect."""
    if db_path == ":memory:":
        # Use shared in-memory URI so schema/seed/data survive across connections
        # in a single process (tests call init + seed via separate connections).
        return ("file:spark_memdb?mode=memory&cache=shared", True)
    return (db_path, False)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and row factory."""
    target, use_uri = _normalize_sqlite_target(db_path or DB_PATH)
    global _SHARED_MEMORY_KEEPALIVE
    if use_uri and _SHARED_MEMORY_KEEPALIVE is None:
        _SHARED_MEMORY_KEEPALIVE = sqlite3.connect(target, uri=True)
        _SHARED_MEMORY_KEEPALIVE.execute("PRAGMA foreign_keys=ON")
    conn = sqlite3.connect(target, uri=use_uri)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database(
    db_path: str | None = None, conn: sqlite3.Connection | None = None
) -> None:
    """Create all tables from schema.sql if they don't exist."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection(db_path)
    schema = _SCHEMA_PATH.read_text()
    try:
        conn.executescript(schema)
    except sqlite3.OperationalError as exc:
        # Backward compatibility for older DBs where graph_event_log was created
        # before newer columns (e.g. category/source_event_id/payload_hash) existed.
        if "no such column: category" not in str(exc):
            raise
        from spark.repositories.redemption import ensure_graph_learning_schema

        ensure_graph_learning_schema(db_path=db_path)
        conn.executescript(schema)
    if owns_connection:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def upsert_venue(conn: sqlite3.Connection, venue: dict[str, Any]) -> None:
    from spark.repositories.venues import upsert_venue as repo_upsert_venue

    repo_upsert_venue(conn, venue)


def upsert_venues(db_path: str | Path | None, venues: list[dict[str, Any]]) -> int:
    from spark.repositories.venues import upsert_venues as repo_upsert_venues

    return repo_upsert_venues(db_path, venues)


def insert_venue_transactions(
    conn: sqlite3.Connection, transactions: list[dict[str, Any]]
) -> int:
    from spark.repositories.transactions import (
        insert_venue_transactions as repo_insert_venue_transactions,
    )

    return repo_insert_venue_transactions(conn, transactions)
