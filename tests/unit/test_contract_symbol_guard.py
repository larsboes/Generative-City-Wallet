from __future__ import annotations

import subprocess
from pathlib import Path


def test_contract_symbol_guard_passes_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["uv", "run", "python", "scripts/dev/check_contract_symbols.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Contract parity check OK" in result.stdout
