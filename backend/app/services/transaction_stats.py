from datetime import date, datetime, time, timedelta, timezone
import sqlite3


def utc_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _summary(count: int, revenue: float) -> dict:
    return {
        "transaction_count": count,
        "total_revenue_eur": round(revenue, 2),
        "avg_ticket_eur": round(revenue / count, 2) if count else 0.0,
    }


def get_hourly_transactions(conn: sqlite3.Connection, merchant_id: str, day: date) -> list[dict]:
    start, end = utc_day_bounds(day)
    rows = conn.execute(
        """
        SELECT hour_of_day, COUNT(*) AS transaction_count, COALESCE(SUM(amount_eur), 0) AS total_revenue_eur
        FROM payone_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        GROUP BY hour_of_day
        """,
        (merchant_id, iso(start), iso(end)),
    ).fetchall()
    by_hour = {int(row["hour_of_day"]): row for row in rows}

    buckets = []
    for hour in range(24):
        row = by_hour.get(hour)
        count = int(row["transaction_count"]) if row else 0
        revenue = float(row["total_revenue_eur"]) if row else 0.0
        buckets.append({"hour": hour, **_summary(count, revenue)})
    return buckets


def get_daily_transactions(conn: sqlite3.Connection, merchant_id: str, day: date) -> dict:
    hourly = get_hourly_transactions(conn, merchant_id, day)
    count = sum(bucket["transaction_count"] for bucket in hourly)
    revenue = sum(bucket["total_revenue_eur"] for bucket in hourly)
    return {"date": day.isoformat(), **_summary(count, revenue), "hourly": hourly}


def get_daily_average(conn: sqlite3.Connection, merchant_id: str, lookback_days: int, end_day: date | None = None) -> dict:
    end_day = end_day or datetime.now(timezone.utc).date()
    start = datetime.combine(end_day - timedelta(days=lookback_days), time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_day, time.min, tzinfo=timezone.utc)
    row = conn.execute(
        """
        SELECT COUNT(*) AS transaction_count, COALESCE(SUM(amount_eur), 0) AS total_revenue_eur
        FROM payone_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        """,
        (merchant_id, iso(start), iso(end)),
    ).fetchone()
    count = int(row["transaction_count"])
    revenue = float(row["total_revenue_eur"])
    divisor = max(1, lookback_days)
    return {
        "lookback_days": lookback_days,
        "avg_daily_transactions": round(count / divisor, 2),
        "avg_daily_revenue_eur": round(revenue / divisor, 2),
        "avg_ticket_eur": round(revenue / count, 2) if count else 0.0,
    }


def get_hourly_average_by_weekday(
    conn: sqlite3.Connection,
    merchant_id: str,
    weekday: int,
    lookback_days: int,
    end_day: date | None = None,
) -> list[dict]:
    end_day = end_day or datetime.now(timezone.utc).date()
    start = datetime.combine(end_day - timedelta(days=lookback_days), time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_day, time.min, tzinfo=timezone.utc)
    matching_days = sum(
        1 for offset in range(lookback_days) if (end_day - timedelta(days=offset + 1)).weekday() == weekday
    )

    rows = conn.execute(
        """
        SELECT hour_of_day, COUNT(*) AS transaction_count, COALESCE(SUM(amount_eur), 0) AS total_revenue_eur
        FROM payone_transactions
        WHERE merchant_id = ?
          AND day_of_week = ?
          AND timestamp >= ?
          AND timestamp < ?
        GROUP BY hour_of_day
        """,
        (merchant_id, weekday, iso(start), iso(end)),
    ).fetchall()
    by_hour = {int(row["hour_of_day"]): row for row in rows}
    divisor = max(1, matching_days)

    buckets = []
    for hour in range(24):
        row = by_hour.get(hour)
        count = int(row["transaction_count"]) if row else 0
        revenue = float(row["total_revenue_eur"]) if row else 0.0
        buckets.append(
            {
                "hour": hour,
                "avg_transaction_count": round(count / divisor, 2),
                "avg_revenue_eur": round(revenue / divisor, 2),
            }
        )
    return buckets


def get_last_7_days_revenue(conn: sqlite3.Connection, merchant_id: str, end_day: date | None = None) -> dict:
    end_day = end_day or datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=6)
    start = datetime.combine(start_day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=timezone.utc)
    rows = conn.execute(
        """
        SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS transaction_count,
               COALESCE(SUM(amount_eur), 0) AS total_revenue_eur
        FROM payone_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        """,
        (merchant_id, iso(start), iso(end)),
    ).fetchall()
    by_day = {row["day"]: row for row in rows}

    days = []
    for offset in range(7):
        current_day = start_day + timedelta(days=offset)
        key = current_day.isoformat()
        row = by_day.get(key)
        count = int(row["transaction_count"]) if row else 0
        revenue = float(row["total_revenue_eur"]) if row else 0.0
        days.append({"date": key, **_summary(count, revenue)})

    return {
        "merchant_id": merchant_id,
        "days": days,
        "total_revenue_eur": round(sum(day["total_revenue_eur"] for day in days), 2),
    }


def get_fastest_slowest_hours(conn: sqlite3.Connection, merchant_id: str, lookback_days: int) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    rows = conn.execute(
        """
        SELECT hour_of_day, COUNT(*) AS transaction_count, COALESCE(SUM(amount_eur), 0) AS total_revenue_eur
        FROM payone_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        GROUP BY hour_of_day
        """,
        (merchant_id, iso(start), iso(end)),
    ).fetchall()
    by_hour = {int(row["hour_of_day"]): row for row in rows}
    divisor = max(1, lookback_days)
    buckets = []

    for hour in range(24):
        row = by_hour.get(hour)
        count = int(row["transaction_count"]) if row else 0
        revenue = float(row["total_revenue_eur"]) if row else 0.0
        buckets.append(
            {
                "hour": hour,
                "avg_transaction_count": round(count / divisor, 2),
                "avg_revenue_eur": round(revenue / divisor, 2),
            }
        )

    ranked = sorted(buckets, key=lambda item: (item["avg_transaction_count"], item["avg_revenue_eur"]))
    return {
        "lookback_days": lookback_days,
        "slowest_hours": ranked[:5],
        "fastest_hours": list(reversed(ranked[-5:])),
    }
