"""Offer generation endpoint."""

from fastapi import APIRouter

from spark.models.api import GenerateOfferBlockedResponse, GenerateOfferRequest
from spark.models.offers import OfferObject
from spark.services.offer_pipeline import generate_offer_pipeline

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])


@router.post("/generate", response_model=OfferObject | GenerateOfferBlockedResponse)
async def generate_offer(request: GenerateOfferRequest):
    return await generate_offer_pipeline(request)
