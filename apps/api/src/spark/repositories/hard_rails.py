from __future__ import annotations

from spark.db.connection import get_connection


def get_merchant_name_and_address(
    merchant_id: str, db_path: str | None = None
) -> tuple[str | None, str | None]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT name, address FROM merchants WHERE id = ?",
            (merchant_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["name"], row["address"]
    finally:
        conn.close()
