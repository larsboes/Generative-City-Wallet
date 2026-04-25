"""Test configuration — ensures src/ is importable."""
import sys
from pathlib import Path

# Add project root to path so `src.backend` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
