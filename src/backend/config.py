"""Spark backend configuration — loads from .env file in project root."""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from project root ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # src/../
load_dotenv(PROJECT_ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────────
_db_path_raw = os.getenv("SPARK_DB_PATH", "data/spark.db")
# Resolve relative paths against project root
DB_PATH = str(PROJECT_ROOT / _db_path_raw) if not os.path.isabs(_db_path_raw) else _db_path_raw

# Ensure data directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────────────
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ── Gemini Flash ───────────────────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

# ── OpenWeatherMap ─────────────────────────────────────────────────────────────
STUTTGART_CITY_ID = "2825297"
WEATHER_CACHE_TTL_SECONDS = 300  # 5 min

# ── Offer defaults ─────────────────────────────────────────────────────────────
DEFAULT_OFFER_VALID_MINUTES = 20
DEFAULT_QR_VALID_MINUTES = 15
HMAC_SECRET = os.getenv("SPARK_HMAC_SECRET", "spark-hackathon-secret-change-me")

# ── Neo4j (User Knowledge Graph) ───────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "spark-neo4j-dev")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
NEO4J_ENABLED = os.getenv("NEO4J_ENABLED", "true").lower() in ("1", "true", "yes")
# How long to wait at startup before giving up and using the fallback path.
NEO4J_STARTUP_TIMEOUT_S = float(os.getenv("NEO4J_STARTUP_TIMEOUT_S", "3.0"))

# ── Graph rule defaults (used by GraphValidationService) ───────────────────────
GRAPH_RULES = {
    # Same merchant cannot be offered more than N times within the lookback window.
    "merchant_fatigue_max_per_day": int(os.getenv("GRAPH_MERCHANT_FATIGUE_MAX", "3")),
    # Cooldown after a non-redeemed offer for the same merchant (minutes).
    "same_merchant_cooldown_min": int(os.getenv("GRAPH_SAME_MERCHANT_COOLDOWN_MIN", "30")),
    # Number of recent offers to inspect for category diversity.
    "category_diversity_window": int(os.getenv("GRAPH_CATEGORY_DIVERSITY_WINDOW", "5")),
    # Maximum offers per session per day (anti-spam guard).
    "session_offer_budget_per_day": int(os.getenv("GRAPH_SESSION_OFFER_BUDGET", "8")),
}
