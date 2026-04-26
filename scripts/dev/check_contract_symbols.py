"""
Guardrail: shared TS contracts and Python Pydantic models should stay aligned.

Checks that a curated set of public contract names appears in both:
  packages/shared/src/contracts.ts
  apps/api/src/spark/models/__init__.py exports

Also validates a small set of critical field-level parities for boundary types.
"""

from __future__ import annotations

import ast
import re
import sys
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
    "SocialPreference",
    "PriceTier",
    "IntentVector",
    "DensitySignal",
    "PlaceContext",
    "EventContext",
    "ExternalContext",
    "DensitySignalType",
    "CouponType",
    "OfferObject",
    "QRPayload",
    "RedemptionValidationRequest",
    "RedemptionValidationResponse",
    "CashbackCredit",
    "GenerateOfferRequest",
    "ContinuityResetRequest",
    "ContinuityResetResponse",
    "OCRTransitPayload",
    "OCRTransitIngestResponse",
    "OCRTransitParseRequest",
    "OCRTransitParseResponse",
    "DemoOverrides",
    "WalletSeedItem",
    "WalletSeedRequest",
    "WalletSeedResponse",
    "CreateWaveRequest",
    "JoinWaveRequest",
    "WaveResponse",
    "JoinWaveResponse",
    "ConflictResolveRequest",
    "ConflictResolveResponse",
)


FIELD_PARITY: dict[str, set[str]] = {
    "IntentVector": {
        "grid_cell",
        "movement_mode",
        "time_bucket",
        "weather_need",
        "social_preference",
        "price_tier",
        "recent_categories",
        "dwell_signal",
        "battery_low",
        "session_id",
        "continuity_hint",
        "activity_signal",
        "activity_source",
        "activity_confidence",
        "location_grid_accuracy_m",
    },
    "PlaceContext": {
        "source",
        "provider_available",
        "nearby_place_count",
        "avg_rating",
        "avg_busyness",
        "popular_place_name",
    },
    "EventContext": {
        "source",
        "provider_available",
        "events_tonight_count",
        "nearest_event_name",
        "cache_hit",
        "error_reason",
        "http_status",
    },
    "ExternalContext": {"place", "events"},
    "DensitySignal": {
        "merchant_id",
        "density_score",
        "drop_pct",
        "signal",
        "offer_eligible",
        "historical_avg",
        "current_rate",
        "current_occupancy_pct",
        "predicted_occupancy_pct",
        "confidence",
        "timestamp",
    },
    "DemoOverrides": {
        "temp_celsius",
        "weather_condition",
        "merchant_occupancy_pct",
        "social_preference",
        "time_bucket",
        "transit_delay_minutes",
        "must_return_by",
    },
    "GenerateOfferRequest": {
        "intent",
        "merchant_id",
        "demo_overrides",
        "transit_delay_minutes",
        "must_return_by",
        "ocr_transit",
    },
    "OCRTransitPayload": {
        "city",
        "district",
        "line",
        "station",
        "transit_delay_minutes",
        "must_return_by",
        "confidence",
    },
    "OCRTransitIngestResponse": {
        "accepted",
        "transit_delay_minutes",
        "must_return_by",
        "confidence",
        "reason",
    },
    "OCRTransitParseRequest": {
        "raw_text",
        "city_hint",
        "district_hint",
        "parser_provider",
    },
    "OCRTransitParseResponse": {
        "parsed",
        "payload",
        "parser_provider",
        "attempts",
        "reason",
    },
    "RedemptionValidationRequest": {"qr_payload", "merchant_id"},
    "CashbackCredit": {
        "session_id",
        "offer_id",
        "amount_eur",
        "merchant_name",
        "credited_at",
        "wallet_balance_eur",
    },
    "WalletSeedItem": {
        "category",
        "weight",
        "source_type",
        "source_confidence",
        "artifact_count",
    },
    "WalletSeedRequest": {"seeds"},
    "WalletSeedResponse": {
        "session_id",
        "applied",
        "skipped",
        "duplicates",
        "suppressed_by_guardrail",
        "avg_quality_multiplier",
        "normalized_source_types",
        "governance_confidence_caps",
    },
    "ContinuityResetRequest": {"session_id", "continuity_hint", "opt_out"},
    "ContinuityResetResponse": {
        "session_id",
        "continuity_id",
        "continuity_hint",
        "source",
        "expires_at",
        "reset_applied",
        "opt_out",
    },
    "CreateWaveRequest": {
        "offer_id",
        "merchant_id",
        "created_by_session",
        "milestone_target",
        "ttl_minutes",
    },
    "JoinWaveRequest": {"session_id"},
    "WaveResponse": {
        "wave_id",
        "offer_id",
        "merchant_id",
        "participant_count",
        "milestone_target",
        "status",
        "expires_at",
        "catalyst_bonus_pct",
    },
    "JoinWaveResponse": {
        "join_applied",
    },
    "OfferObject": {
        "offer_id",
        "session_id",
        "merchant",
        "discount",
        "content",
        "genui",
        "expires_at",
        "qr_payload",
        "explainability",
    },
}


def _must_have_ts_symbols(path: Path, names: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    missing = []
    for n in names:
        e = re.escape(n)
        pattern = rf"(?:export\s+(?:type|interface)\s+{e}\b|type\s+{e}\s*=)"
        if not re.search(pattern, text):
            missing.append(n)
    return missing


def _extract_python_exports(py_init_path: Path) -> set[str]:
    tree = ast.parse(py_init_path.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                exports.add(elt.value)
    return exports


def _extract_python_class_fields(models_dir: Path) -> dict[str, set[str]]:
    classes: dict[str, set[str]] = {}
    for file in models_dir.glob("*.py"):
        if file.name in {"__init__.py", "contracts.py"}:
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                fields: set[str] = set()
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(
                        stmt.target, ast.Name
                    ):
                        fields.add(stmt.target.id)
                classes[node.name] = fields
    return classes


def _must_have_python_exports(exported: set[str], names: tuple[str, ...]) -> list[str]:
    missing = [n for n in names if n not in exported]
    return missing


def _field_parity_errors(
    ts_text: str,
    py_class_fields: dict[str, set[str]],
    checks: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    for symbol, required_fields in checks.items():
        ts_interface_match = re.search(
            rf"export\s+interface\s+{re.escape(symbol)}(?:\s+extends\s+[A-Za-z0-9_,\s]+)?\s*\{{(?P<body>.*?)\n\}}",
            ts_text,
            re.DOTALL,
        )
        ts_fields: set[str] = set()
        if ts_interface_match:
            for line in ts_interface_match.group("body").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("//"):
                    continue
                m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??\s*:", stripped)
                if m:
                    ts_fields.add(m.group(1))

        py_fields = py_class_fields.get(symbol, set())
        missing_ts = sorted(required_fields - ts_fields)
        missing_py = sorted(required_fields - py_fields)
        if missing_ts:
            errors.append(f"{symbol}: TS missing fields {missing_ts}")
        if missing_py:
            errors.append(f"{symbol}: Python missing fields {missing_py}")

    return errors


def _report_missing(label: str, path: Path, missing: list[str], root: Path) -> None:
    if missing:
        print(f"{label} ({path.relative_to(root)}): missing {missing}", file=sys.stderr)


def main() -> int:
    root = _repo_root()
    ts_path = root / "packages" / "shared" / "src" / "contracts.ts"
    py_init_path = root / "apps" / "api" / "src" / "spark" / "models" / "__init__.py"
    py_models_dir = py_init_path.parent
    for p in (ts_path, py_init_path):
        if not p.is_file():
            print(f"Missing file: {p}", file=sys.stderr)
            return 2

    ts_missing = _must_have_ts_symbols(ts_path, SYMBOLS)
    py_exports = _extract_python_exports(py_init_path)
    py_missing = _must_have_python_exports(py_exports, SYMBOLS)

    _report_missing("TS", ts_path, ts_missing, root)
    _report_missing("Python exports", py_init_path, py_missing, root)

    ts_text = ts_path.read_text(encoding="utf-8")
    py_class_fields = _extract_python_class_fields(py_models_dir)
    parity_errors = _field_parity_errors(ts_text, py_class_fields, FIELD_PARITY)
    if parity_errors:
        for err in parity_errors:
            print(f"Field parity: {err}", file=sys.stderr)

    if ts_missing or py_missing or parity_errors:
        return 1
    print(
        f"Contract parity check OK ({len(SYMBOLS)} symbols, {len(FIELD_PARITY)} field-level checks)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
