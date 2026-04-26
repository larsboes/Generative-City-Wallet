from __future__ import annotations

from spark.db.connection import get_connection


def insert_offer_audit_log(values: tuple, db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, grid_cell, movement_mode,
                social_preference, merchant_id, density_signal, density_score,
                current_occupancy_pct, predicted_occupancy_pct,
                conflict_check, conflict_resolution, framing_band,
                coupon_type, coupon_config,
                llm_raw_output, final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        conn.commit()
    finally:
        conn.close()
