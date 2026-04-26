from __future__ import annotations

from types import SimpleNamespace

from spark.services import offer_pipeline as pipeline


def _offer_stub(value: float = 10.0):
    return SimpleNamespace(discount=SimpleNamespace(value=value, source="merchant_rules_db"))


def test_apply_wave_bonus_to_offer_increases_discount(monkeypatch):
    monkeypatch.setattr(
        "spark.services.offer_pipeline.get_session_wave_bonus_for_merchant",
        lambda **kwargs: 0.2,  # noqa: ARG005
    )
    offer = _offer_stub(10.0)

    bonus = pipeline._apply_wave_bonus_to_offer(
        offer=offer,
        session_id="sess-wave-bonus",
        merchant_id="MERCHANT_001",
    )

    assert bonus == 0.2
    assert offer.discount.value == 12.0
    assert offer.discount.source == "spark_wave_catalyst_bonus"


def test_apply_wave_bonus_to_offer_noop_when_no_bonus(monkeypatch):
    monkeypatch.setattr(
        "spark.services.offer_pipeline.get_session_wave_bonus_for_merchant",
        lambda **kwargs: 0.0,  # noqa: ARG005
    )
    offer = _offer_stub(9.0)

    bonus = pipeline._apply_wave_bonus_to_offer(
        offer=offer,
        session_id="sess-wave-bonus-none",
        merchant_id="MERCHANT_001",
    )

    assert bonus == 0.0
    assert offer.discount.value == 9.0
    assert offer.discount.source == "merchant_rules_db"
