"""
Payone density endpoints.
"""

from fastapi import APIRouter
from fastapi import HTTPException

from spark.models.transactions import (
    PayoneDensityResponse,
    PayoneIngestRequest,
    PayoneIngestResponse,
    PayoneMerchantDensityResponse,
)
from spark.services.density import (
    compute_density_signal,
    get_all_merchants_density,
)
from spark.services.payone_ingest import ingest_payone_event as ingest_payone_event_service

router = APIRouter(prefix="/api/payone", tags=["payone"])


@router.get("/density/{merchant_id}", response_model=PayoneDensityResponse)
async def density_endpoint(merchant_id: str) -> PayoneDensityResponse:
    """Get current density signal for a merchant."""
    return compute_density_signal(merchant_id)


@router.get("/merchants", response_model=list[PayoneMerchantDensityResponse])
async def merchants_endpoint() -> list[PayoneMerchantDensityResponse]:
    """List all merchants with current density signals."""
    return get_all_merchants_density()


@router.post("/ingest", response_model=PayoneIngestResponse)
async def ingest_payone_event(request: PayoneIngestRequest) -> PayoneIngestResponse:
    """
    Ingest a validated payone/fluentbit event into payone_transactions.

    This endpoint is intentionally lightweight so Fluent Bit can post events
    directly in compose deployments.
    """
    try:
        return ingest_payone_event_service(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"ingest_failed: {exc}") from exc
