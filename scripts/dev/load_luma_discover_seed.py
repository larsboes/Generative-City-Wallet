"""
Legacy wrapper for Luma Discover seed loader.

Preferred command (uv):
  uv run python -m spark.services.luma_discover_loader --lat 48.7758 --lng 9.1829 --radius 50000
"""

from spark.services.luma_discover_loader import main


if __name__ == "__main__":
    raise SystemExit(main())
