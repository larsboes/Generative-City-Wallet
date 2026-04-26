"""
Neo4j async driver lifecycle, safe execution helper, and lightweight metrics.

The client is intentionally fail-soft: if the database is unavailable the
backend keeps producing offers using SQLite + heuristic fallbacks. We
latch the unavailable state so we don't repeatedly hammer a dead instance
during a request.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, TypeVar

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from spark.config import (
    NEO4J_DATABASE,
    NEO4J_ENABLED,
    NEO4J_PASSWORD,
    NEO4J_STARTUP_TIMEOUT_S,
    NEO4J_URI,
    NEO4J_USER,
)
from spark.utils.logger import get_logger

logger = get_logger("spark.graph")

T = TypeVar("T")

_driver: Optional[AsyncDriver] = None
_init_lock: Optional[asyncio.Lock] = None
_unavailable: bool = not NEO4J_ENABLED

_metrics: dict[str, Any] = {
    "queries_total": 0,
    "queries_failed": 0,
    "last_error": None,
    "last_success_at": None,
    "last_failure_at": None,
    "total_latency_ms": 0.0,
}


def _lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def init_graph(*, run_schema: bool = True) -> bool:
    """
    Best-effort initialize the Neo4j driver. Never raises.

    Returns True if the driver is connected, False otherwise.
    """
    global _driver, _unavailable
    if not NEO4J_ENABLED:
        _unavailable = True
        logger.info("Neo4j disabled via NEO4J_ENABLED=false — using fallback path.")
        return False
    if _driver is not None:
        return True

    async with _lock():
        if _driver is not None:
            return True
        try:
            driver = AsyncGraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
            )
            await asyncio.wait_for(
                driver.verify_connectivity(), timeout=NEO4J_STARTUP_TIMEOUT_S
            )
            _driver = driver
            _unavailable = False
            logger.info("Neo4j connected at %s (db=%s)", NEO4J_URI, NEO4J_DATABASE)
        except Exception as exc:
            _unavailable = True
            _driver = None
            logger.warning(
                "Neo4j unavailable at %s (%s) — backend continues with fallback.",
                NEO4J_URI,
                exc,
            )
            return False

    if run_schema:
        # Lazy import to avoid circular dependency at module import time.
        from spark.graph.schema import ensure_schema
        from spark.graph.migrations import apply_migrations

        await safe_execute(ensure_schema, fallback=None, op_name="ensure_schema")
        await safe_execute(apply_migrations, fallback=None, op_name="apply_migrations")

    return True


async def close_graph() -> None:
    global _driver
    drv = _driver
    _driver = None
    if drv is not None:
        try:
            await drv.close()
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Neo4j close failed: %s", exc)


def is_available() -> bool:
    return _driver is not None and not _unavailable


def get_metrics() -> dict[str, Any]:
    """Return a snapshot of the runtime metrics (safe to expose in /health)."""
    snap = dict(_metrics)
    queries = snap["queries_total"] or 1
    snap["avg_latency_ms"] = round(snap["total_latency_ms"] / queries, 2)
    snap["available"] = is_available()
    snap["enabled"] = NEO4J_ENABLED
    return snap


@asynccontextmanager
async def session() -> AsyncIterator[AsyncSession]:
    """Yield a Neo4j async session bound to the configured database."""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    async with _driver.session(database=NEO4J_DATABASE) as s:
        yield s


async def safe_execute(
    fn: Callable[[AsyncSession], Awaitable[T]],
    fallback: T,
    *,
    op_name: str = "neo4j_op",
) -> T:
    """
    Execute a graph callable inside a session and return `fallback`
    on any failure. Records metrics for observability.
    """
    if _driver is None or _unavailable:
        return fallback

    start = time.perf_counter()
    _metrics["queries_total"] += 1
    try:
        async with _driver.session(database=NEO4J_DATABASE) as s:
            result = await fn(s)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        _metrics["total_latency_ms"] += elapsed_ms
        _metrics["last_success_at"] = time.time()
        # Clear stale error once a graph op succeeds.
        _metrics["last_error"] = None
        return result
    except Exception as exc:
        _metrics["queries_failed"] += 1
        _metrics["last_error"] = f"{op_name}: {exc.__class__.__name__}: {exc}"
        _metrics["last_failure_at"] = time.time()
        logger.warning("Neo4j %s failed: %s", op_name, exc)
        return fallback
