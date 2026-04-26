from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "infra" / "pipeline" / "graph-maintenance.py"
)
SPEC = importlib.util.spec_from_file_location("run_graph_maintenance", MODULE_PATH)
assert SPEC and SPEC.loader
run_graph_maintenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_graph_maintenance)


def test_graph_maintenance_reports_decay_health_alarm(monkeypatch):
    class FakeRepo:
        async def cleanup_old_data(self, retention_days: int):  # noqa: ANN001
            return {"sessions": 0, "offers": 0}

        async def decay_stale_preferences(  # noqa: ANN001
            self, stale_after_days: int, default_decay_rate: float
        ):
            return {"processed": 1.0, "updated": 1.0}

    async def fake_init_graph() -> bool:
        return True

    async def fake_close_graph() -> None:
        return None

    monkeypatch.setattr(run_graph_maintenance, "init_graph", fake_init_graph)
    monkeypatch.setattr(run_graph_maintenance, "close_graph", fake_close_graph)
    monkeypatch.setattr(run_graph_maintenance, "get_repository", lambda: FakeRepo())
    monkeypatch.setattr(run_graph_maintenance, "cleanup_expired_waves", lambda: 0)
    monkeypatch.setattr(
        run_graph_maintenance,
        "get_latest_graph_event_timestamp",
        lambda event_type: "2000-01-01T00:00:00+00:00",
    )

    result = asyncio.run(
        run_graph_maintenance._run(
            retention_days=30,
            stale_after_days=7,
            decay_rate=0.01,
            decay_max_gap_hours=12,
        )
    )

    assert result["connected"] is True
    assert result["health"]["decay_gap_alarm"] is True
    assert result["retention"]["wallet_seed_pruned"] >= 0
