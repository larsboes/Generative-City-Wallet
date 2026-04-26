"""
Spark Backend — FastAPI application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spark.config import (
    DB_PATH,
    GRAPH_PREF_DECAY_DEFAULT_RATE,
    GRAPH_PREF_DECAY_ENABLED,
    GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
    GRAPH_RETENTION_DAYS,
    GRAPH_RUN_CLEANUP_ON_STARTUP,
)
from spark.db.connection import init_database
from spark.db.seed import seed_database
from spark.graph import close_graph, get_metrics, init_graph, is_available
from spark.graph.repository import get_repository
from spark.graph.seed import sync_merchants_from_sqlite
from spark.routers import (
    context,
    graph,
    occupancy,
    ocr,
    offers,
    payone,
    redemption,
    transactions,
    vendors,
    wave,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite + Neo4j on startup; shut down driver on exit."""
    if not Path(DB_PATH).exists():
        print("🔥 First run — seeding database...")
        seed_database()
    else:
        init_database()

    connected = await init_graph()
    if connected:
        await sync_merchants_from_sqlite()
        if GRAPH_RUN_CLEANUP_ON_STARTUP:
            repo = get_repository()
            await repo.cleanup_old_data(retention_days=GRAPH_RETENTION_DAYS)
            if GRAPH_PREF_DECAY_ENABLED:
                await repo.decay_stale_preferences(
                    stale_after_days=GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
                    default_decay_rate=GRAPH_PREF_DECAY_DEFAULT_RATE,
                )

    try:
        yield
    finally:
        await close_graph()


app = FastAPI(
    title="Spark Backend",
    description="Real-time, context-aware local commerce offers powered by Payone density signals + Gemini Flash",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Lovable frontend, local dev, and any demo origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wide open for hackathon — lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(payone.router)
app.include_router(context.router)
app.include_router(offers.router)
app.include_router(redemption.router)
app.include_router(graph.router)
app.include_router(occupancy.router)
app.include_router(ocr.router)
app.include_router(transactions.router)
app.include_router(vendors.router)
app.include_router(wave.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "spark-backend",
        "version": "0.1.0",
        "graph": {
            "available": is_available(),
            "metrics": get_metrics(),
        },
    }
