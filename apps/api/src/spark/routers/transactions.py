from fastapi import APIRouter

from spark.models.transactions import (
    LiveUpdateRequest,
    TransactionGenerationRequest,
    TransactionGenerationResponse,
)
from spark.routers.errors import as_bad_request, as_not_found
from spark.services.transaction_generation import generate_history, generate_live_update

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


@router.post("/generate/history", response_model=TransactionGenerationResponse)
def api_generate_history(
    request: TransactionGenerationRequest,
) -> TransactionGenerationResponse:
    try:
        result = generate_history(
            merchant_ids=request.merchant_ids,
            category=request.category,
            city=request.city,
            limit=request.limit,
            days=request.days,
            start=request.start,
            end=request.end,
            seed=request.seed,
        )
    except ValueError as exc:
        raise as_bad_request(exc) from exc
    except LookupError as exc:
        raise as_not_found(exc) from exc

    return TransactionGenerationResponse(
        inserted_count=result.inserted,
        venue_count=result.venue_count,
        start=result.start,
        end=result.end,
        source="synthetic_history",
    )


@router.post("/generate/live-update", response_model=TransactionGenerationResponse)
def api_generate_live_update(
    request: LiveUpdateRequest,
) -> TransactionGenerationResponse:
    try:
        result = generate_live_update(
            merchant_ids=request.merchant_ids,
            category=request.category,
            city=request.city,
            limit=request.limit,
            timestamp=request.timestamp,
            seed=request.seed,
        )
    except LookupError as exc:
        raise as_not_found(exc) from exc

    return TransactionGenerationResponse(
        inserted_count=result.inserted,
        venue_count=result.venue_count,
        start=result.window_start,
        end=result.window_end,
        source="synthetic_live_update",
    )
