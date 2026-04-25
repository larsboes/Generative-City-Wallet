"""Test configuration — ensures src/ is importable and DB is seeded."""
import sys
from pathlib import Path

# Add project root to path so `src.backend` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force DB to data/spark.db and pre-seed if empty
from src.backend.config import DB_PATH
from src.backend.db.seed import seed_database

if not Path(DB_PATH).exists():
    seed_database()
