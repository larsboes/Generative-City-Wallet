from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from spark.models.context import DemoOverrides, IntentVector


class GenerateOfferRequest(BaseModel):
    """Request accepted by the offer generation endpoint."""

    intent: IntentVector
    merchant_id: Optional[str] = None
    demo_overrides: Optional[DemoOverrides] = None

