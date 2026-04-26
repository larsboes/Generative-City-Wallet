from __future__ import annotations

from datetime import datetime
import uuid

from fastapi.testclient import TestClient

from spark.db.connection import get_connection, init_database
from spark.main import app


def test_wave_two_session_progression():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-{uuid.uuid4()}"
    creator_session = f"sess-creator-{run_id}"
    friend_session = f"sess-friend-{run_id}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                offer_id,
                datetime.now().isoformat(),
                creator_session,
                "MERCHANT_001",
                "{}",
                "{}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        created = client.post(
            "/api/waves",
            json={
                "offer_id": offer_id,
                "merchant_id": "MERCHANT_001",
                "created_by_session": creator_session,
                "milestone_target": 2,
                "ttl_minutes": 30,
            },
        )
        assert created.status_code == 200
        wave_id = created.json()["wave_id"]
        assert created.json()["participant_count"] == 1
        assert created.json()["catalyst_bonus_pct"] == 0.125

        joined = client.post(
            f"/api/waves/{wave_id}/join",
            json={"session_id": friend_session},
        )
        assert joined.status_code == 200
        assert joined.json()["participant_count"] == 2
        assert joined.json()["status"] == "COMPLETED"
        assert joined.json()["catalyst_bonus_pct"] == 0.2
        assert joined.json()["join_applied"] is True

        # Replay join from same session should not increment again.
        replay = client.post(
            f"/api/waves/{wave_id}/join",
            json={"session_id": friend_session},
        )
        assert replay.status_code == 200
        assert replay.json()["participant_count"] == 2
        assert replay.json()["status"] == "COMPLETED"
        assert replay.json()["catalyst_bonus_pct"] == 0.2
        assert replay.json()["join_applied"] is False


def test_wave_expired_not_joinable():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-expired-{uuid.uuid4()}"
    creator_session = f"sess-creator-expired-{run_id}"
    friend_session = f"sess-friend-expired-{run_id}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                offer_id,
                datetime.now().isoformat(),
                creator_session,
                "MERCHANT_001",
                "{}",
                "{}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        created = client.post(
            "/api/waves",
            json={
                "offer_id": offer_id,
                "merchant_id": "MERCHANT_001",
                "created_by_session": creator_session,
                "milestone_target": 2,
                "ttl_minutes": 5,
            },
        )
        assert created.status_code == 200
        wave_id = created.json()["wave_id"]

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE spark_waves SET expires_at = ? WHERE wave_id = ?",
                ("2000-01-01T00:00:00+00:00", wave_id),
            )
            conn.commit()
        finally:
            conn.close()

        joined = client.post(
            f"/api/waves/{wave_id}/join",
            json={"session_id": friend_session},
        )
        assert joined.status_code == 404


def test_wave_cleanup_endpoint_marks_expired_rows():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-cleanup-{uuid.uuid4()}"
    creator_session = f"sess-creator-cleanup-{run_id}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                offer_id,
                datetime.now().isoformat(),
                creator_session,
                "MERCHANT_001",
                "{}",
                "{}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        created = client.post(
            "/api/waves",
            json={
                "offer_id": offer_id,
                "merchant_id": "MERCHANT_001",
                "created_by_session": creator_session,
                "milestone_target": 3,
                "ttl_minutes": 5,
            },
        )
        assert created.status_code == 200
        wave_id = created.json()["wave_id"]

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE spark_waves SET expires_at = ? WHERE wave_id = ?",
                ("2000-01-01T00:00:00+00:00", wave_id),
            )
            conn.commit()
        finally:
            conn.close()

        cleanup = client.post("/api/waves/cleanup")
        assert cleanup.status_code == 200
        assert cleanup.json()["cleaned"] >= 1

        get_wave = client.get(f"/api/waves/{wave_id}")
        assert get_wave.status_code == 200
        assert get_wave.json()["status"] == "EXPIRED"


def test_wave_participant_cap_prevents_additional_joins():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-cap-{uuid.uuid4()}"
    creator_session = f"sess-creator-cap-{run_id}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                offer_id,
                datetime.now().isoformat(),
                creator_session,
                "MERCHANT_001",
                "{}",
                "{}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        created = client.post(
            "/api/waves",
            json={
                "offer_id": offer_id,
                "merchant_id": "MERCHANT_001",
                "created_by_session": creator_session,
                "milestone_target": 20,
                "ttl_minutes": 30,
            },
        )
        assert created.status_code == 200
        wave_id = created.json()["wave_id"]

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE spark_waves SET milestone_target = 999 WHERE wave_id = ?",
                (wave_id,),
            )
            conn.commit()
        finally:
            conn.close()

        for idx in range(2, 51):
            joined = client.post(
                f"/api/waves/{wave_id}/join",
                json={"session_id": f"sess-cap-{run_id}-{idx}"},
            )
            assert joined.status_code == 200
            assert joined.json()["join_applied"] is True

        capped_join = client.post(
            f"/api/waves/{wave_id}/join",
            json={"session_id": f"sess-cap-{run_id}-51"},
        )
        assert capped_join.status_code == 200
        assert capped_join.json()["participant_count"] == 50
        assert capped_join.json()["join_applied"] is False
