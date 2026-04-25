"""Spark backend configuration — loads from .env file in project root."""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from repository root (walk up for pyproject.toml) ───────────────
def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[3]  # spark → apps/api/src → apps/api → repo


PROJECT_ROOT = _repo_root()
load_dotenv(PROJECT_ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────────
_db_path_raw = os.getenv("SPARK_DB_PATH", "data/spark.db")
# Resolve relative paths against project root
DB_PATH = (
    str(PROJECT_ROOT / _db_path_raw)
    if not os.path.isabs(_db_path_raw)
    else _db_path_raw
)

# Ensure data directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────────────
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ── Gemini Flash ───────────────────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

# ── Offer LLM (server dev path; on-device Gemma lives in React Native native code)
# gemini = default | ollama = local /api/chat for dev without Google API key
OFFER_LLM_PROVIDER = os.getenv("OFFER_LLM_PROVIDER", "gemini").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# ── Strands Agent ──────────────────────────────────────────────────────────────
AGENT_ENABLED = os.getenv("AGENT_ENABLED", "auto").lower()
# "auto" = enabled when GOOGLE_AI_API_KEY is set, "true"/"false" for explicit override
if AGENT_ENABLED == "auto":
    AGENT_ENABLED = bool(GOOGLE_AI_API_KEY)
else:
    AGENT_ENABLED = AGENT_ENABLED in ("1", "true", "yes")

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
    "same_merchant_cooldown_min": int(
        os.getenv("GRAPH_SAME_MERCHANT_COOLDOWN_MIN", "30")
    ),
    # Number of recent offers to inspect for category diversity.
    "category_diversity_window": int(os.getenv("GRAPH_CATEGORY_DIVERSITY_WINDOW", "5")),
    # Maximum offers per session per day (anti-spam guard).
    "session_offer_budget_per_day": int(os.getenv("GRAPH_SESSION_OFFER_BUDGET", "8")),
    # Fairness: max share any single category can take in recent window.
    # Set to 1.0 to effectively disable.
    "fairness_max_category_share": float(
        os.getenv("GRAPH_FAIRNESS_MAX_CATEGORY_SHARE", "1.0")
    ),
    # Window of recent offers considered for fairness.
    "fairness_window": int(os.getenv("GRAPH_FAIRNESS_WINDOW", "10")),
    # Minimum observations before fairness can block.
    "fairness_min_observations": int(os.getenv("GRAPH_FAIRNESS_MIN_OBSERVATIONS", "6")),
}

# ── Graph retention / housekeeping ─────────────────────────────────────────────
GRAPH_RETENTION_DAYS = int(os.getenv("GRAPH_RETENTION_DAYS", "30"))
GRAPH_RUN_CLEANUP_ON_STARTUP = os.getenv(
    "GRAPH_RUN_CLEANUP_ON_STARTUP", "true"
).lower() in ("1", "true", "yes")

# Preference-edge retention and decay controls.
GRAPH_PREF_EDGE_RETENTION_DAYS = int(os.getenv("GRAPH_PREF_EDGE_RETENTION_DAYS", "90"))
GRAPH_PREF_DECAY_ENABLED = os.getenv("GRAPH_PREF_DECAY_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)
GRAPH_PREF_DECAY_STALE_AFTER_DAYS = int(
    os.getenv("GRAPH_PREF_DECAY_STALE_AFTER_DAYS", "7")
)
GRAPH_PREF_DECAY_DEFAULT_RATE = float(
    os.getenv("GRAPH_PREF_DECAY_DEFAULT_RATE", "0.01")
)
