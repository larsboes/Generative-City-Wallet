"""
Hard rails enforcement.
Post-LLM guard — runs ALWAYS before returning an offer to the device.
Rule: if in doubt, the DB wins. The LLM never determines what the user owes.
"""

import re
from datetime import datetime, timedelta

from src.backend.db.connection import get_connection
from src.backend.models.contracts import (
    AuditInfo,
    CompositeContextState,
    DiscountInfo,
    LLMOfferOutput,
    MerchantInfo,
    OfferObject,
)
from src.backend.config import DEFAULT_OFFER_VALID_MINUTES

# ── Banned copy patterns (GDPR / regulatory) ──────────────────────────────────

BANNED_COPY_PATTERNS = [
    "helps you",
    "good for your health",
    "improves",
    "boosts your",
    "doctors recommend",
    "clinically",
    "heals",
    "hilft dir",
    "gesund",
    "verbessert",
    "steigert dein",
    "ärzte empfehlen",
    "klinisch",
    "heilt",
]


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

    # 2. Discount — capped to what merchant configured
    max_discount = state.merchant.active_coupon.max_discount_pct
    discount_type = "percentage"
    if state.merchant.active_coupon.type == "DRINK":
        discount_type = "drink"
    elif state.merchant.active_coupon.type == "MILESTONE":
        discount_type = "cover_refund"
    elif state.merchant.active_coupon.type is None:
        discount_type = "none"
        max_discount = 0

    # 3. Replace placeholders in content
    content = llm_output.content.model_copy()
    content.headline = _replace_placeholders(
        content.headline, merchant_name, max_discount, DEFAULT_OFFER_VALID_MINUTES
    )
    content.subtext = _replace_placeholders(
        content.subtext, merchant_name, max_discount, DEFAULT_OFFER_VALID_MINUTES
    )
    content.cta_text = _replace_placeholders(
        content.cta_text, merchant_name, max_discount, DEFAULT_OFFER_VALID_MINUTES
    )
    if content.emotional_hook:
        content.emotional_hook = _replace_placeholders(
            content.emotional_hook,
            merchant_name,
            max_discount,
            DEFAULT_OFFER_VALID_MINUTES,
        )

    # 4. Strip banned health claims
    for field_name in ["headline", "subtext", "emotional_hook"]:
        text = getattr(content, field_name, "") or ""
        for pattern in BANNED_COPY_PATTERNS:
            if pattern.lower() in text.lower():
                setattr(content, field_name, "[content review required]")

    # 5. Compute expiry server-side
    now = datetime.now()
    valid_window = (
        state.merchant.active_coupon.valid_window_min or DEFAULT_OFFER_VALID_MINUTES
    )
    expires_at = (now + timedelta(minutes=valid_window)).isoformat()

    # 6. Build audit info
    AuditInfo(
        rails_applied=True,
        discount_original_llm=0,  # LLM doesn't generate discount numbers
        discount_capped_to=max_discount,
        composite_state_hash=str(hash(state.timestamp + state.session_id)),
    )

    return OfferObject(
        offer_id=offer_id,
        session_id=state.session_id,
        merchant=MerchantInfo(
            id=state.merchant.id,
            name=merchant_name,
            distance_m=state.merchant.distance_m,
            address=merchant_address,
            category=state.merchant.category,
        ),
        discount=DiscountInfo(
            value=max_discount,
            type=discount_type,
            source="merchant_rules_db",
        ),
        content=content,
        genui=llm_output.genui,
        expires_at=expires_at,
    )


def _replace_placeholders(
    text: str, merchant_name: str, discount: float, expiry_min: int
) -> str:
    """Replace [MERCHANT_NAME], [DISCOUNT]%, [EXPIRY_MIN] with real values."""
    text = text.replace("[MERCHANT_NAME]", merchant_name)
    text = text.replace("[DISCOUNT]%", f"{int(discount)} %")
    text = text.replace("[DISCOUNT] %", f"{int(discount)} %")
    text = re.sub(r"\[DISCOUNT\]", str(int(discount)), text)
    text = text.replace("[EXPIRY_MIN]", str(expiry_min))
    return text
