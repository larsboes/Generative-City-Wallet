"""
Payone density endpoints.
"""

from fastapi import APIRouter

from src.backend.services.density import compute_density_signal, get_all_merchants_density

router = APIRouter(prefix="/api/payone", tags=["payone"])


@router.get("/density/{merchant_id}")
async def density_endpoint(merchant_id: str):
    """Get current density signal for a merchant."""
    return compute_density_signal(merchant_id)


@router.get("/merchants")
async def merchants_endpoint():
    """List all merchants with current density signals."""
    return get_all_merchants_density()
