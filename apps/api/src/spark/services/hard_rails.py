"""
Hard rails enforcement.
Post-LLM guard — runs ALWAYS before returning an offer to the device.
Rule: if in doubt, the DB wins. The LLM never determines what the user owes.
"""

from spark.db.connection import get_connection
from spark.models.context import CompositeContextState
from spark.models.offers import LLMOfferOutput, OfferObject
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
    conn = get_connection(db_path)

    # 1. Merchant name — always from DB
    merchant_row = conn.execute(
        "SELECT name, address FROM merchants WHERE id = ?",
        (state.merchant.id,),
    ).fetchone()
    conn.close()

    merchant_name = merchant_row["name"] if merchant_row else state.merchant.name
    merchant_address = (
        merchant_row["address"] if merchant_row else state.merchant.address
    )

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
