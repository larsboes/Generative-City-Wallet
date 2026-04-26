from __future__ import annotations

from fastapi import APIRouter, HTTPException

from spark.models.wave import (
    CreateWaveRequest,
    JoinWaveRequest,
    JoinWaveResponse,
    WaveResponse,
)
from spark.services.wave import (
    cleanup_expired_waves,
    create_wave_record,
    get_wave_record,
    join_wave_record,
)

router = APIRouter(prefix="/api/waves", tags=["waves"])


@router.post("", response_model=WaveResponse)
async def create_wave_endpoint(request: CreateWaveRequest):
    wave = create_wave_record(
        offer_id=request.offer_id,
        merchant_id=request.merchant_id,
        created_by_session=request.created_by_session,
        milestone_target=request.milestone_target,
        ttl_minutes=request.ttl_minutes,
    )
    if not wave:
        raise HTTPException(status_code=400, detail="wave_create_failed")
    return WaveResponse(**wave)


@router.post("/{wave_id}/join", response_model=JoinWaveResponse)
async def join_wave_endpoint(wave_id: str, request: JoinWaveRequest):
    joined = join_wave_record(wave_id=wave_id, session_id=request.session_id)
    if not joined:
        raise HTTPException(status_code=404, detail="wave_not_joinable")
    wave, join_applied = joined
    return JoinWaveResponse(**wave, join_applied=join_applied)


@router.get("/{wave_id}", response_model=WaveResponse)
async def get_wave_endpoint(wave_id: str):
    wave = get_wave_record(wave_id=wave_id)
    if not wave:
        raise HTTPException(status_code=404, detail="wave_not_found")
    return WaveResponse(**wave)


@router.post("/cleanup")
async def cleanup_waves_endpoint():
    cleaned = cleanup_expired_waves()
    return {"cleaned": cleaned}
