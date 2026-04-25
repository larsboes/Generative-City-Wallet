"""
Guardrail: shared TS contracts and Python Pydantic models should stay aligned.

Checks that a curated set of public contract names appears in both:
  packages/shared/src/contracts.ts
  apps/api/src/spark/models/contracts.py

Extend SYMBOLS when you add cross-boundary types. This is intentionally shallow
(full structural parity is still a human / OpenAPI follow-up).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Could not locate repo root (pyproject.toml)")


SYMBOLS = (
    "MovementMode",
    "WeatherNeed",
    "IntentVector",
    "DensitySignal",
    "DensitySignalType",
    "CouponType",
    "OfferObject",
    "QRPayload",
    "RedemptionValidationResponse",
    "CashbackCredit",
    "GenerateOfferRequest",
    "DemoOverrides",
)


def _must_have(
    root: Path,
    path: Path,
    build_pattern: Callable[[str], str],
    label: str,
    names: tuple[str, ...],
) -> list[str]:
    text = path.read_text(encoding="utf-8")
    missing = [n for n in names if not re.search(build_pattern(n), text)]
    if missing:
        print(f"{label} ({path.relative_to(root)}): missing {missing}", file=sys.stderr)
    return missing


def main() -> int:
    root = _repo_root()
    ts_path = root / "packages" / "shared" / "src" / "contracts.ts"
    py_path = root / "apps" / "api" / "src" / "spark" / "models" / "contracts.py"
    for p in (ts_path, py_path):
        if not p.is_file():
            print(f"Missing file: {p}", file=sys.stderr)
            return 2

    def ts_pat(name: str) -> str:
        e = re.escape(name)
        return rf"(?:export\s+(?:type|interface)\s+{e}\b|type\s+{e}\s*=)"

    def py_pat(name: str) -> str:
        return rf"class\s+{re.escape(name)}\b"

    ts_missing = _must_have(root, ts_path, ts_pat, "TS", SYMBOLS)
    py_missing = _must_have(root, py_path, py_pat, "Python", SYMBOLS)
    if ts_missing or py_missing:
        return 1
    print(f"Contract symbol check OK ({len(SYMBOLS)} names in TS + Python).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
