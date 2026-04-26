from __future__ import annotations

from spark.repositories.wave import create_wave, expire_old_waves, get_wave, join_wave


def create_wave_record(
    *,
    offer_id: str,
    merchant_id: str,
    created_by_session: str,
    milestone_target: int,
    ttl_minutes: int,
):
    expire_old_waves()
    return create_wave(
        offer_id=offer_id,
        merchant_id=merchant_id,
        created_by_session=created_by_session,
        milestone_target=milestone_target,
        ttl_minutes=ttl_minutes,
    )


def join_wave_record(*, wave_id: str, session_id: str):
    return join_wave(wave_id=wave_id, session_id=session_id)


def get_wave_record(*, wave_id: str):
    expire_old_waves()
    return get_wave(wave_id=wave_id)


def cleanup_expired_waves() -> int:
    """Operational cleanup hook for scheduled jobs and admin routes."""
    return expire_old_waves()
