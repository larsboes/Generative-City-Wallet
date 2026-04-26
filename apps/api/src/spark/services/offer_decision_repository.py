from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from spark.db.connection import get_connection


@dataclass(frozen=True)
class CandidateMerchantRecord:
    merchant_id: str
    merchant_category: str


@dataclass(frozen=True)
class OfferDecisionSessionState:
    unresolved_offer_id: str | None
    offers_last_24h: int


class OfferDecisionRepository:
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

    def list_candidate_merchants(self, *, grid_cell: str) -> list[CandidateMerchantRecord]:
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT id, type FROM merchants WHERE grid_cell = ?",
                (grid_cell,),
            ).fetchall()
            if not rows:
                rows = conn.execute("SELECT id, type FROM merchants LIMIT 5").fetchall()
            return [
                CandidateMerchantRecord(
                    merchant_id=row["id"],
                    merchant_category=row["type"],
                )
                for row in rows
            ]
        finally:
            conn.close()
