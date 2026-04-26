from __future__ import annotations

from datetime import datetime
import uuid

from fastapi.testclient import TestClient

from spark.db.connection import get_connection, init_database
from spark.main import app
from spark.services.redemption import confirm_redemption


def _insert_offer_row(offer_id: str, session_id: str) -> None:
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
                session_id,
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

        cleanup_again = client.post("/api/waves/cleanup")
        assert cleanup_again.status_code == 200
        assert cleanup_again.json()["cleaned"] == 0


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


def test_wave_create_rate_limit_rejects_immediate_duplicate_create():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-rate-{uuid.uuid4()}"
    creator_session = f"sess-creator-rate-{run_id}"
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

    payload = {
        "offer_id": offer_id,
        "merchant_id": "MERCHANT_001",
        "created_by_session": creator_session,
        "milestone_target": 3,
        "ttl_minutes": 30,
    }

    with TestClient(app) as client:
        created = client.post("/api/waves", json=payload)
        assert created.status_code == 200

        duplicate = client.post("/api/waves", json=payload)
        assert duplicate.status_code == 400
        assert duplicate.json()["detail"] == "wave_create_failed"


def test_wave_create_blocks_when_too_many_active_waves_for_session():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    creator_session = f"sess-creator-active-cap-{run_id}"

    with TestClient(app) as client:
        for idx in range(1, 5):
            offer_id = f"offer-wave-active-cap-{run_id}-{idx}"
            _insert_offer_row(offer_id, creator_session)
            created = client.post(
                "/api/waves",
                json={
                    "offer_id": offer_id,
                    "merchant_id": "MERCHANT_001",
                    "created_by_session": creator_session,
                    "milestone_target": 3,
                    "ttl_minutes": 30,
                },
            )
            if idx <= 3:
                assert created.status_code == 200
            else:
                assert created.status_code == 400
                assert created.json()["detail"] == "wave_create_failed"


def test_wave_join_blocks_when_session_exceeds_burst_limit():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    joining_session = f"sess-joiner-burst-{run_id}"
    wave_ids: list[str] = []

    with TestClient(app) as client:
        for idx in range(1, 14):
            offer_id = f"offer-wave-join-burst-{run_id}-{idx}"
            creator_session = f"sess-wave-owner-{run_id}-{idx}"
            _insert_offer_row(offer_id, creator_session)
            created = client.post(
                "/api/waves",
                json={
                    "offer_id": offer_id,
                    "merchant_id": "MERCHANT_001",
                    "created_by_session": creator_session,
                    "milestone_target": 5,
                    "ttl_minutes": 30,
                },
            )
            assert created.status_code == 200
            wave_ids.append(created.json()["wave_id"])

        for idx, wave_id in enumerate(wave_ids, start=1):
            joined = client.post(
                f"/api/waves/{wave_id}/join",
                json={"session_id": joining_session},
            )
            if idx <= 12:
                assert joined.status_code == 200
                assert joined.json()["join_applied"] is True
            else:
                assert joined.status_code == 404


def test_wave_bonus_is_consumed_by_redemption_cashback():
    init_database()
    run_id = uuid.uuid4().hex[:8]
    offer_id = f"offer-wave-redeem-{uuid.uuid4()}"
    creator_session = f"sess-wave-redeem-{run_id}"

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
                '{"offer_id":"%s","session_id":"%s","merchant":{"name":"Wave Cafe"},"discount":{"value":20},"content":{"headline":"x","subtext":"y","cta_text":"z"},"genui":{"color_palette":"soft_cream","typography_weight":"semibold","background_style":"clean","imagery_prompt":"cafe","urgency_style":"low","card_mood":"cozy"},"expires_at":"2026-04-26T12:00:00"}'
                % (offer_id, creator_session),
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

        joined = client.post(
            f"/api/waves/{wave_id}/join",
            json={"session_id": f"sess-wave-redeem-friend-{run_id}"},
        )
        assert joined.status_code == 200
        assert joined.json()["status"] == "COMPLETED"
        assert joined.json()["catalyst_bonus_pct"] == 0.2

    redemption = confirm_redemption(offer_id)
    assert redemption["success"] is True
    assert redemption["base_amount_eur"] == 1.0
    assert redemption["catalyst_bonus_pct"] == 0.2
    assert redemption["amount_eur"] == 1.2
