"""Test configuration — DB seed; `spark` is on PYTHONPATH (see pyproject.toml)."""

import sys
from pathlib import Path

# Add project root to path so `spark` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force DB to data/spark.db and pre-seed if empty
from spark.config import DB_PATH
from spark.db.seed import seed_database

if not Path(DB_PATH).exists():
    seed_database()
