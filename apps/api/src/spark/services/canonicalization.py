"""
Canonicalization helpers for runtime-owned mapping boundaries.

These helpers convert raw or semi-trusted inputs into authoritative Python
objects while recording what was rewritten, defaulted, or derived.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Generic, Mapping, TypeVar

from pydantic import BaseModel, ValidationError

from spark.config import DEFAULT_OFFER_VALID_MINUTES
from spark.models.context import ActiveCoupon, CompositeContextState
from spark.models.offers import (
    AuditInfo,
    DiscountInfo,
    LLMContent,
    LLMGenUI,
    LLMOfferOutput,
    MerchantInfo,
    OfferObject,
)

T = TypeVar("T")


class MappingReason(str, Enum):
    DB_OVERRIDE_APPLIED = "db_override_applied"
    FIELD_REWRITTEN = "field_rewritten"
    FIELD_DEFAULTED = "field_defaulted"
    FIELD_DERIVED = "field_derived"
    FIELD_DROPPED = "field_dropped"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    BANNED_COPY_REDACTED = "banned_copy_redacted"
    STORED_JSON_INVALID = "stored_json_invalid"
    CATEGORY_NORMALIZED = "category_normalized"


class MappingAction(BaseModel):
    field: str
    reason: MappingReason
    message: str
    original_value: Any | None = None
    normalized_value: Any | None = None


@dataclass
class CanonicalizationResult(Generic[T]):
    value: T | None
    actions: list[MappingAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class NormalizedVenueTransaction(BaseModel):
    transaction_id: str
    merchant_id: str
    category: str
    timestamp: str
    hour_of_day: int
    day_of_week: int
    hour_of_week: int
    amount_eur: float
    currency: str = "EUR"
    source: str = "synthetic"


CATEGORY_ALIASES: dict[str, str] = {
    "food_court": "fast_food",
    "ice_cream": "cafe",
    "coffee_shop": "cafe",
    "club": "nightclub",
}

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


def normalize_category(category: str | None) -> str:
    if not category:
        return "unknown"
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    return CATEGORY_ALIASES.get(normalized, normalized)


def hour_of_week(dt: datetime) -> int:
    return dt.weekday() * 24 + dt.hour


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return ensure_utc(dt).isoformat()


def _replace_placeholders(
    text: str, merchant_name: str, discount: float, expiry_min: int
) -> str:
    text = text.replace("[MERCHANT_NAME]", merchant_name)
    text = text.replace("[DISCOUNT]%", f"{int(discount)} %")
    text = text.replace("[DISCOUNT] %", f"{int(discount)} %")
    text = re.sub(r"\[DISCOUNT\]", str(int(discount)), text)
    text = text.replace("[EXPIRY_MIN]", str(expiry_min))
    return text


def _discount_type(active_coupon: ActiveCoupon) -> tuple[str, float]:
    max_discount = active_coupon.max_discount_pct
    if active_coupon.type == "DRINK":
        return "drink", max_discount
    if active_coupon.type == "MILESTONE":
        return "cover_refund", max_discount
    if active_coupon.type is None:
        return "none", 0
    return "percentage", max_discount


def canonicalize_offer(
    *,
    llm_output: LLMOfferOutput,
    state: CompositeContextState,
    offer_id: str,
    merchant_name: str,
    merchant_address: str,
) -> CanonicalizationResult[OfferObject]:
    actions: list[MappingAction] = [
        MappingAction(
            field="merchant.name",
            reason=MappingReason.DB_OVERRIDE_APPLIED,
            message="Merchant name is sourced from DB/state truth.",
            original_value=state.merchant.name,
            normalized_value=merchant_name,
        ),
        MappingAction(
            field="merchant.address",
            reason=MappingReason.DB_OVERRIDE_APPLIED,
            message="Merchant address is sourced from DB/state truth.",
            original_value=state.merchant.address,
            normalized_value=merchant_address,
        ),
    ]

    discount_type, max_discount = _discount_type(state.merchant.active_coupon)
    actions.append(
        MappingAction(
            field="discount",
            reason=MappingReason.DB_OVERRIDE_APPLIED,
            message="Discount value and type come from merchant coupon config.",
            original_value=0,
            normalized_value={"value": max_discount, "type": discount_type},
        )
    )

    valid_window = (
        state.merchant.active_coupon.valid_window_min or DEFAULT_OFFER_VALID_MINUTES
    )
    expires_at = (datetime.now() + timedelta(minutes=valid_window)).isoformat()
    actions.append(
        MappingAction(
            field="expires_at",
            reason=MappingReason.FIELD_DERIVED,
            message="Offer expiry is computed server-side from the coupon window.",
            normalized_value=expires_at,
        )
    )

    content_fields = {
        "headline": llm_output.content.headline,
        "subtext": llm_output.content.subtext,
        "cta_text": llm_output.content.cta_text,
        "emotional_hook": llm_output.content.emotional_hook,
    }
    normalized_content: dict[str, str | None] = {}
    for field_name, original_text in content_fields.items():
        if not original_text:
            fallback = None if field_name == "emotional_hook" else ""
            normalized_content[field_name] = fallback
            if fallback == "":
                actions.append(
                    MappingAction(
                        field=f"content.{field_name}",
                        reason=MappingReason.FIELD_DEFAULTED,
                        message="Missing content field defaulted to empty string.",
                        normalized_value=fallback,
                    )
                )
            continue

        replaced = _replace_placeholders(
            original_text, merchant_name, max_discount, valid_window
        )
        if replaced != original_text:
            actions.append(
                MappingAction(
                    field=f"content.{field_name}",
                    reason=MappingReason.FIELD_REWRITTEN,
                    message="Offer placeholders replaced with canonical values.",
                    original_value=original_text,
                    normalized_value=replaced,
                )
            )
        redacted = replaced
        for pattern in BANNED_COPY_PATTERNS:
            if pattern.lower() in redacted.lower():
                redacted = "[content review required]"
                actions.append(
                    MappingAction(
                        field=f"content.{field_name}",
                        reason=MappingReason.BANNED_COPY_REDACTED,
                        message=f"Banned copy pattern '{pattern}' was redacted.",
                        original_value=replaced,
                        normalized_value=redacted,
                    )
                )
                break
        normalized_content[field_name] = redacted

    offer = OfferObject(
        offer_id=offer_id,
        session_id=state.session_id,
        merchant=MerchantInfo(
            id=state.merchant.id,
            name=merchant_name,
            distance_m=state.merchant.distance_m,
            address=merchant_address,
            category=normalize_category(state.merchant.category),
        ),
        discount=DiscountInfo(
            value=max_discount,
            type=discount_type,
            source="merchant_rules_db",
        ),
        content=LLMContent(
            headline=str(normalized_content["headline"] or ""),
            subtext=str(normalized_content["subtext"] or ""),
            cta_text=str(normalized_content["cta_text"] or ""),
            emotional_hook=normalized_content["emotional_hook"],
        ),
        genui=llm_output.genui,
        expires_at=expires_at,
        audit_info=AuditInfo(
            rails_applied=True,
            discount_original_llm=0,
            discount_capped_to=max_discount,
            composite_state_hash=str(hash(state.timestamp + state.session_id)),
            mapping_actions=[action.model_dump(mode="json") for action in actions],
        ),
    )
    return CanonicalizationResult(value=offer, actions=actions)


def parse_stored_offer(raw_offer: str | None) -> CanonicalizationResult[OfferObject]:
    actions: list[MappingAction] = []
    if not raw_offer:
        actions.append(
            MappingAction(
                field="final_offer",
                reason=MappingReason.FIELD_DEFAULTED,
                message="Missing stored offer payload.",
            )
        )
        return CanonicalizationResult(value=None, actions=actions, errors=["missing"])

    try:
        return CanonicalizationResult(value=OfferObject.model_validate_json(raw_offer))
    except ValidationError as exc:
        errors = [str(exc)]
    except Exception as exc:
        errors = [str(exc)]

    actions.append(
        MappingAction(
            field="final_offer",
            reason=MappingReason.STORED_JSON_INVALID,
            message="Stored offer JSON could not be parsed into OfferObject.",
            original_value=raw_offer,
        )
    )
    try:
        parsed = json.loads(raw_offer)
    except json.JSONDecodeError as exc:
        return CanonicalizationResult(value=None, actions=actions, errors=errors + [str(exc)])

    merchant = parsed.get("merchant") or {}
    discount = parsed.get("discount") or {}
    content = parsed.get("content") or {}
    genui = parsed.get("genui") or {}
    fallback = OfferObject(
        offer_id=str(parsed.get("offer_id") or ""),
        session_id=str(parsed.get("session_id") or ""),
        merchant=MerchantInfo(
            id=str(merchant.get("id") or ""),
            name=str(merchant.get("name") or "Unknown"),
            distance_m=float(merchant.get("distance_m") or 0),
            address=str(merchant.get("address") or ""),
            category=normalize_category(merchant.get("category")),
        ),
        discount=DiscountInfo(
            value=float(discount.get("value") or 0),
            type=str(discount.get("type") or "percentage"),
            source=str(discount.get("source") or "merchant_rules_db"),
        ),
        content=LLMContent(
            headline=str(content.get("headline") or ""),
            subtext=str(content.get("subtext") or ""),
            cta_text=str(content.get("cta_text") or ""),
            emotional_hook=content.get("emotional_hook"),
        ),
        genui=llm_output_from_dict(genui),
        expires_at=str(parsed.get("expires_at") or ""),
        qr_payload=parsed.get("qr_payload"),
    )
    actions.append(
        MappingAction(
            field="final_offer",
            reason=MappingReason.FIELD_REWRITTEN,
            message="Stored offer payload fell back to partial canonical defaults.",
            normalized_value=fallback.model_dump(mode="json"),
        )
    )
    return CanonicalizationResult(value=fallback, actions=actions, errors=errors)


def llm_output_from_dict(genui: Mapping[str, Any]) -> LLMGenUI:
    try:
        return LLMGenUI(
            color_palette=str(genui.get("color_palette") or "warm_amber"),
            typography_weight=str(genui.get("typography_weight") or "medium"),
            background_style=str(genui.get("background_style") or "gradient"),
            imagery_prompt=str(genui.get("imagery_prompt") or "contextual offer card"),
            urgency_style=str(genui.get("urgency_style") or "static"),
            card_mood=str(genui.get("card_mood") or "cozy"),
        )
    except ValidationError:
        return LLMGenUI(
            color_palette="warm_amber",
            typography_weight="medium",
            background_style="gradient",
            imagery_prompt="contextual offer card",
            urgency_style="static",
            card_mood="cozy",
        )


def canonicalize_venue_transaction(
    transaction: Mapping[str, Any],
) -> CanonicalizationResult[NormalizedVenueTransaction]:
    actions: list[MappingAction] = []
    category = normalize_category(transaction.get("category"))
    if category != transaction.get("category"):
        actions.append(
            MappingAction(
                field="category",
                reason=MappingReason.CATEGORY_NORMALIZED,
                message="Transaction category normalized to canonical alias.",
                original_value=transaction.get("category"),
                normalized_value=category,
            )
        )

    timestamp_raw = transaction.get("timestamp")
    if isinstance(timestamp_raw, datetime):
        dt = ensure_utc(timestamp_raw)
    else:
        dt = ensure_utc(datetime.fromisoformat(str(timestamp_raw)))

    derived = {
        "hour_of_day": dt.hour,
        "day_of_week": dt.weekday(),
        "hour_of_week": hour_of_week(dt),
    }
    for field_name, value in derived.items():
        if transaction.get(field_name) != value:
            actions.append(
                MappingAction(
                    field=field_name,
                    reason=MappingReason.FIELD_DERIVED,
                    message=f"{field_name} derived from canonical timestamp.",
                    original_value=transaction.get(field_name),
                    normalized_value=value,
                )
            )

    currency = str(transaction.get("currency") or "EUR")
    if not transaction.get("currency"):
        actions.append(
            MappingAction(
                field="currency",
                reason=MappingReason.FIELD_DEFAULTED,
                message="Currency defaulted to EUR.",
                normalized_value=currency,
            )
        )

    source = str(transaction.get("source") or "synthetic")
    if not transaction.get("source"):
        actions.append(
            MappingAction(
                field="source",
                reason=MappingReason.FIELD_DEFAULTED,
                message="Transaction source defaulted to synthetic.",
                normalized_value=source,
            )
        )

    normalized = NormalizedVenueTransaction(
        transaction_id=str(transaction["transaction_id"]),
        merchant_id=str(transaction["merchant_id"]),
        category=category,
        timestamp=iso(dt),
        hour_of_day=derived["hour_of_day"],
        day_of_week=derived["day_of_week"],
        hour_of_week=derived["hour_of_week"],
        amount_eur=float(transaction["amount_eur"]),
        currency=currency,
        source=source,
    )
    return CanonicalizationResult(value=normalized, actions=actions)
