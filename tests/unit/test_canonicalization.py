import json

from spark.services.canonicalization import (
    MappingReason,
    canonicalize_venue_transaction,
    parse_stored_offer,
)


def test_parse_stored_offer_falls_back_for_malformed_payload() -> None:
    raw_offer = json.dumps(
        {
            "offer_id": "offer-1",
            "session_id": "sess-1",
            "merchant": {"name": "Cafe Fallback", "category": "coffee shop"},
            "discount": {"value": 12},
            "content": {"headline": "Hi", "subtext": "There", "cta_text": "Now"},
            "genui": {"color_palette": "not-a-real-color"},
        }
    )

    result = parse_stored_offer(raw_offer)

    assert result.value is not None
    assert result.value.merchant.name == "Cafe Fallback"
    assert result.value.merchant.category == "cafe"
    assert result.value.discount.value == 12
    assert result.value.genui.color_palette == "warm_amber"
    assert result.errors
    assert any(
        action.reason == MappingReason.STORED_JSON_INVALID for action in result.actions
    )


def test_canonicalize_venue_transaction_derives_fields_and_normalizes_category() -> (
    None
):
    result = canonicalize_venue_transaction(
        {
            "transaction_id": "txn-1",
            "merchant_id": "merchant-1",
            "category": "coffee shop",
            "timestamp": "2026-04-20T09:15:00+00:00",
            "amount_eur": "7.5",
        }
    )

    assert result.value is not None
    assert result.value.category == "cafe"
    assert result.value.hour_of_day == 9
    assert result.value.day_of_week == 0
    assert result.value.hour_of_week == 9
    reasons = {action.reason for action in result.actions}
    assert MappingReason.CATEGORY_NORMALIZED in reasons
    assert MappingReason.FIELD_DERIVED in reasons
    assert MappingReason.FIELD_DEFAULTED in reasons
