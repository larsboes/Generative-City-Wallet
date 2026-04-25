"""
Context endpoints — composite state builder.
"""

from fastapi import APIRouter

from spark.models.contracts import IntentVector, DemoOverrides
from spark.services.composite import build_composite_state

router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("/composite")
async def composite_endpoint(
    intent: IntentVector,
    merchant_id: str | None = None,
    demo_overrides: DemoOverrides | None = None,
):
    """
    Build the full CompositeContextState from an intent vector.
    Supports demo_overrides for the Context Slider.
    """
    state = await build_composite_state(intent, merchant_id, demo_overrides)
    return state
