"""CLI wrapper — delegates to seed_database() for one-shot Munich demo load."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "api" / "src"))

from spark.db.seed import seed_database

if __name__ == "__main__":
    seed_database()
