"""
Spark Backend — FastAPI application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import DB_PATH
from src.backend.db.connection import init_database
from src.backend.db.seed import seed_database
from src.backend.graph import close_graph, get_metrics, init_graph, is_available
from src.backend.graph.seed import sync_merchants_from_sqlite
from src.backend.routers import context, graph, offers, payone, redemption


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
