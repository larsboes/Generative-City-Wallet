from spark.db.connection import get_connection, init_database
from spark.models.common import (
    ConflictRecommendation,
    MovementMode,
    PriceTier,
    SocialPreference,
    WeatherNeed,
)
from spark.models.context import (
    ActiveCoupon,
    CompositeContextState,
    ConflictResolutionContext,
    EnvironmentContext,
    IntentVector,
    MerchantContext,
    MerchantDemand,
    UserContext,
)
from spark.models.offers import LLMOfferOutput
from spark.services.hard_rails import enforce_hard_rails
from spark.services.location_cells import latlon_to_h3

TEST_CELL = latlon_to_h3(48.137154, 11.576124)


def _build_state() -> CompositeContextState:
    intent = IntentVector(
        grid_cell=TEST_CELL,
        movement_mode=MovementMode.BROWSING,
        time_bucket="monday_morning_coffee",
        weather_need=WeatherNeed.NEUTRAL,
        social_preference=SocialPreference.QUIET,
        price_tier=PriceTier.MID,
        session_id="sess-1",
    )
    return CompositeContextState(
        timestamp="2026-04-26T10:00:00",
        session_id="sess-1",
        user=UserContext(
            intent=intent,
            preference_scores={"cafe": 0.8},
            social_preference=SocialPreference.QUIET,
            price_tier=PriceTier.MID,
        ),
        merchant=MerchantContext(
            id="merchant-1",
            name="State Cafe",
            category="coffee shop",
            distance_m=120,
            address="State Street 1",
            demand=MerchantDemand(
                density_score=0.4,
                drop_pct=0.6,
                signal="PRIORITY",
                offer_eligible=True,
            ),
            active_coupon=ActiveCoupon(
                type="FLASH", max_discount_pct=15, valid_window_min=25
            ),
        ),
        environment=EnvironmentContext(
            weather_condition="clear",
            temp_celsius=14,
            feels_like_celsius=12,
            weather_need="neutral",
            vibe_signal="calm",
        ),
        conflict_resolution=ConflictResolutionContext(
            recommendation=ConflictRecommendation.RECOMMEND,
            framing_band="quiet_intentional",
        ),
    )


def test_hard_rails_canonicalizes_and_records_audit(tmp_path) -> None:
    db_path = str(tmp_path / "rails.db")
    init_database(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("merchant-1", "DB Cafe", "cafe", 48.1, 11.5, "DB Street 9", TEST_CELL),
        )
        conn.commit()
    finally:
        conn.close()

    llm_output = LLMOfferOutput(
        content={
            "headline": "Warm up at [MERCHANT_NAME]",
            "subtext": "This helps you and saves [DISCOUNT]%",
            "cta_text": "In [EXPIRY_MIN]",
            "emotional_hook": "Only at [MERCHANT_NAME]",
        },
        genui={
            "color_palette": "warm_amber",
            "typography_weight": "medium",
            "background_style": "gradient",
            "imagery_prompt": "cozy cafe",
            "urgency_style": "gentle_pulse",
            "card_mood": "cozy",
        },
        framing_band_used="quiet_intentional",
    )

    offer = enforce_hard_rails(llm_output, _build_state(), "offer-1", db_path=db_path)

    assert offer.merchant.name == "DB Cafe"
    assert offer.merchant.address == "DB Street 9"
    assert offer.merchant.category == "cafe"
    assert offer.discount.value == 15
    assert offer.content.headline == "Warm up at DB Cafe"
    assert offer.content.subtext == "[content review required]"
    assert offer.content.cta_text == "In 25"
    assert offer.audit_info is not None
    reasons = {action["reason"] for action in offer.audit_info.mapping_actions}
    assert "db_override_applied" in reasons
    assert "field_rewritten" in reasons
    assert "banned_copy_redacted" in reasons
