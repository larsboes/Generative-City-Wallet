"""
Context endpoints — composite state builder.
"""

from fastapi import APIRouter, Depends

from spark.domain.interfaces import IGraphRepository
from spark.graph.repository import get_repository
from spark.models.context import CompositeContextState, DemoOverrides, IntentVector
from spark.services.composite import build_composite_state, build_provider_probe_intent

router = APIRouter(prefix="/api/v1/context", tags=["context"])


def get_graph_repo() -> IGraphRepository:
    """FastAPI dependency: provides the concrete graph repository."""
    return get_repository()


@router.post("/composite", response_model=CompositeContextState)
async def composite_endpoint(
    intent: IntentVector,
    merchant_id: str | None = None,
    demo_overrides: DemoOverrides | None = None,
    graph_repo: IGraphRepository = Depends(get_graph_repo),
):
    """
    Build the full CompositeContextState from an intent vector.
    Supports demo_overrides for the Context Slider.
    """
    state = await build_composite_state(
        intent, merchant_id, demo_overrides, graph_repo=graph_repo
    )
    return state


@router.get("/provider-status")
async def provider_status_endpoint(grid_cell: str = "891f8d7a49bffff"):
    """
    Lightweight key/setup verification for external context providers.
    Returns provider status in one response without requiring mobile payloads.
    """
    intent = build_provider_probe_intent(grid_cell)
    state = await build_composite_state(intent=intent)
    return {
        "grid_cell": grid_cell,
        "weather": {
            "source": state.environment.source,
            "provider_available": state.environment.provider_available,
            "cache_hit": state.environment.cache_hit,
            "weather_need": state.environment.weather_need,
            "temp_celsius": state.environment.temp_celsius,
        },
        "external": state.external.model_dump(mode="json") if state.external else None,
    }
