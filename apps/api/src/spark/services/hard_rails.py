"""
Hard rails enforcement.
Post-LLM guard — runs ALWAYS before returning an offer to the device.
Rule: if in doubt, the DB wins. The LLM never determines what the user owes.
"""

from spark.models.context import CompositeContextState
from spark.models.offers import LLMOfferOutput, OfferObject
from spark.repositories.hard_rails import get_merchant_name_and_address
from spark.services.canonicalization import canonicalize_offer


def enforce_hard_rails(
    llm_output: LLMOfferOutput,
    state: CompositeContextState,
    offer_id: str,
    db_path: str | None = None,
) -> OfferObject:
    """
    Post-LLM guard. Run this ALWAYS before returning an offer to the device.
    The DB wins over the LLM for all hard values.
    """
    # 1. Merchant name — always from DB
    merchant_name, merchant_address = get_merchant_name_and_address(
        state.merchant.id, db_path
    )
    merchant_name = merchant_name or state.merchant.name
    merchant_address = merchant_address or state.merchant.address

    result = canonicalize_offer(
        llm_output=llm_output,
        state=state,
        offer_id=offer_id,
        merchant_name=merchant_name,
        merchant_address=merchant_address,
    )
    if result.value is None:
        raise ValueError("Offer canonicalization failed")
    return result.value
