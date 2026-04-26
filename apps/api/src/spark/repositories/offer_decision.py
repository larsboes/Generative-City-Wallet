from __future__ import annotations

from datetime import datetime, timedelta

from spark.db.connection import get_connection
from spark.domain.interfaces import (
    CandidateMerchant,
    IOfferDecisionRepository,
    SessionState,
)
from spark.services.location_cells import is_valid_h3, neighbor_cells

# Backwards-compatible aliases for any external code that imported these names.
CandidateMerchantRecord = CandidateMerchant
OfferDecisionSessionState = SessionState


class OfferDecisionRepository(IOfferDecisionRepository):
    LOCAL_CANDIDATE_LIMIT = 5
    GLOBAL_FALLBACK_LIMIT = 5

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def get_session_state(
        self, *, session_id: str, now: datetime
    ) -> OfferDecisionSessionState:
        conn = get_connection(self.db_path)
        try:
            unresolved = conn.execute(
                """
                SELECT offer_id FROM offer_audit_log
                WHERE session_id = ?
                  AND status IN ('SENT', 'ACCEPTED')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            today_count = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM offer_audit_log
                WHERE session_id = ?
                  AND datetime(created_at) >= datetime(?)
                """,
                (session_id, (now - timedelta(hours=24)).isoformat()),
            ).fetchone()
            return OfferDecisionSessionState(
                unresolved_offer_id=unresolved["offer_id"] if unresolved else None,
                offers_last_24h=int(today_count["c"]) if today_count else 0,
            )
        finally:
            conn.close()

    def list_candidate_merchants(
        self, *, grid_cell: str
    ) -> list[CandidateMerchantRecord]:
        conn = get_connection(self.db_path)
        try:
            rows: list[dict] = []
            seen_ids: set[str] = set()

            def _append_records(records) -> None:  # noqa: ANN001
                for row in records:
                    if row["id"] in seen_ids:
                        continue
                    seen_ids.add(row["id"])
                    rows.append(row)
                    if len(rows) >= self.LOCAL_CANDIDATE_LIMIT:
                        return

            if is_valid_h3(grid_cell):
                same_cell = conn.execute(
                    """
                    SELECT id, type, grid_cell, lat, lon
                    FROM merchants
                    WHERE grid_cell = ?
                    ORDER BY id
                    """,
                    (grid_cell,),
                ).fetchall()
                _append_records(same_cell)

                for ring_k in (1, 2):
                    if len(rows) >= self.LOCAL_CANDIDATE_LIMIT:
                        break
                    neighbor_ring = neighbor_cells(grid_cell, ring_k)
                    if not neighbor_ring:
                        continue
                    placeholders = ",".join("?" for _ in neighbor_ring)
                    nearby = conn.execute(
                        f"""
                        SELECT id, type, grid_cell, lat, lon
                        FROM merchants
                        WHERE grid_cell IN ({placeholders})
                        ORDER BY id
                        """,
                        tuple(neighbor_ring),
                    ).fetchall()
                    _append_records(nearby)

            if not rows:
                rows = conn.execute(
                    """
                    SELECT id, type, grid_cell, lat, lon
                    FROM merchants
                    ORDER BY id
                    LIMIT ?
                    """,
                    (self.GLOBAL_FALLBACK_LIMIT,),
                ).fetchall()

            return [
                CandidateMerchantRecord(
                    merchant_id=row["id"],
                    merchant_category=row["type"],
                    merchant_grid_cell=row["grid_cell"],
                    merchant_lat=row["lat"],
                    merchant_lon=row["lon"],
                )
                for row in rows
            ]
        finally:
            conn.close()
