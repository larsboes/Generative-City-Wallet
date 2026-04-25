"""
Stakeholder conflict resolution rule engine.
Pure rules — no LLM. Deterministic. Auditable.
The LLM runs AFTER this returns RECOMMEND — it only generates framing copy.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.backend.services.density import infer_occupancy_pct, predict_occupancy_at


# ── Framing vocabulary (what the LLM is allowed/banned from saying) ────────────

FRAMING_VOCABULARY: dict[str, list[str]] = {
    "empty_but_filling": [
        "Gerade erst geöffnet",
        "Sei einer der Ersten",
        "VIP-Zeitfenster",
        "Der Abend beginnt hier",
    ],
    "building_momentum": [
        "Es wird gerade lebendig",
        "Komm dazu, bevor es voll wird",
        "Füllt sich gerade",
        "Jetzt ist der richtige Moment",
    ],
    "quiet_intentional": [
        "Ruhig und bereit für dich",
        "Dein Platz wartet",
        "Keine Schlange, kein Warten",
        "Die Ruhe, die du brauchst",
    ],
    "busy": [
        "Gerade richtig was los",
        "Letzte Plätze verfügbar",
    ],
}

BANNED_IF_EMPTY: list[str] = [
    "buzzing",
    "packed",
    "full house",
    "lively",
    "electric atmosphere",
    "everyone's here",
    "the place to be tonight",
    "voll",
    "ausgebucht",
    "brechend voll",
    "elektrisierend",
    "alle sind hier",
    "der Ort des Abends",
]


@dataclass
class ConflictResolution:
    recommendation: str  # RECOMMEND | RECOMMEND_WITH_FRAMING | DO_NOT_RECOMMEND
    framing_band: str | None
    coupon_mechanism: str | None
    reason: str
    recheck_in_minutes: int | None
    allowed_vocabulary: list[str]
    banned_vocabulary: list[str]


def resolve_conflict(
    merchant_id: str,
    user_social_pref: str,
    current_txn_rate: float,
    current_dt: datetime | str,
    active_coupon: dict | None = None,
    db_path: str | None = None,
) -> ConflictResolution:
    """Pure rule engine. No LLM. Deterministic."""
    if isinstance(current_dt, str):
        current_dt = datetime.fromisoformat(current_dt)

    walk_time_min = 2
    arrival_dt = current_dt + timedelta(minutes=walk_time_min + 1)

    current_occ = infer_occupancy_pct(merchant_id, current_txn_rate)
    predicted_occ = predict_occupancy_at(
        merchant_id, current_occ or 0, current_dt, arrival_dt, db_path
    )

    current_occ_pct = (current_occ or 0) * 100
    predicted_occ_pct = predicted_occ * 100

    if user_social_pref == "social":
        if predicted_occ_pct >= 60:
            band = "busy" if predicted_occ_pct >= 70 else "building_momentum"
            coupon = (
                None
                if predicted_occ_pct >= 70
                else _select_coupon(active_coupon, "soft")
            )
            return ConflictResolution(
                recommendation="RECOMMEND",
                framing_band=band,
                coupon_mechanism=coupon,
                reason=f"Social user, predicted occ at arrival {predicted_occ_pct:.0f}% — natural match",
                recheck_in_minutes=None,
                allowed_vocabulary=FRAMING_VOCABULARY.get(band, []),
                banned_vocabulary=[],
            )

        elif predicted_occ_pct >= 40:
            if active_coupon and active_coupon.get("type") == "MILESTONE":
                return ConflictResolution(
                    recommendation="RECOMMEND_WITH_FRAMING",
                    framing_band="building_momentum",
                    coupon_mechanism="MILESTONE",
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + milestone active — honest social proof",
                    recheck_in_minutes=None,
                    allowed_vocabulary=FRAMING_VOCABULARY["building_momentum"],
                    banned_vocabulary=BANNED_IF_EMPTY,
                )
            elif active_coupon and active_coupon.get("type") in ("TIME_BOUND", "DRINK"):
                return ConflictResolution(
                    recommendation="RECOMMEND_WITH_FRAMING",
                    framing_band="empty_but_filling",
                    coupon_mechanism=active_coupon["type"],
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + value coupon — worth the early arrival",
                    recheck_in_minutes=None,
                    allowed_vocabulary=FRAMING_VOCABULARY["empty_but_filling"],
                    banned_vocabulary=BANNED_IF_EMPTY,
                )
            else:
                return ConflictResolution(
                    recommendation="DO_NOT_RECOMMEND",
                    framing_band=None,
                    coupon_mechanism=None,
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + no coupon — insufficient",
                    recheck_in_minutes=30,
                    allowed_vocabulary=[],
                    banned_vocabulary=BANNED_IF_EMPTY,
                )

        else:
            return ConflictResolution(
                recommendation="DO_NOT_RECOMMEND",
                framing_band=None,
                coupon_mechanism=None,
                reason=f"Social user, predicted occ {predicted_occ_pct:.0f}% — won't be lively",
                recheck_in_minutes=30,
                allowed_vocabulary=[],
                banned_vocabulary=BANNED_IF_EMPTY,
            )

    elif user_social_pref == "quiet":
        if current_occ_pct <= 50:
            return ConflictResolution(
                recommendation="RECOMMEND",
                framing_band="quiet_intentional",
                coupon_mechanism=None,
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — natural match",
                recheck_in_minutes=None,
                allowed_vocabulary=FRAMING_VOCABULARY["quiet_intentional"],
                banned_vocabulary=BANNED_IF_EMPTY,
            )
        elif current_occ_pct <= 70:
            return ConflictResolution(
                recommendation="RECOMMEND_WITH_FRAMING",
                framing_band="quiet_intentional",
                coupon_mechanism=_select_coupon(active_coupon, "soft"),
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — some quiet spots remain",
                recheck_in_minutes=None,
                allowed_vocabulary=FRAMING_VOCABULARY["quiet_intentional"],
                banned_vocabulary=BANNED_IF_EMPTY,
            )
        else:
            return ConflictResolution(
                recommendation="DO_NOT_RECOMMEND",
                framing_band=None,
                coupon_mechanism=None,
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — wrong vibe entirely",
                recheck_in_minutes=60,
                allowed_vocabulary=[],
                banned_vocabulary=[],
            )

    else:  # neutral
        return ConflictResolution(
            recommendation="RECOMMEND",
            framing_band=None,
            coupon_mechanism=_select_coupon(active_coupon, "any"),
            reason="Neutral user — standard offer flow, no occupancy constraint",
            recheck_in_minutes=None,
            allowed_vocabulary=[],
            banned_vocabulary=[],
        )


def _select_coupon(active_coupon: dict | None, preference: str) -> str | None:
    if not active_coupon:
        return None
    coupon_type = active_coupon.get("type")
    if preference == "any":
        return coupon_type
    if preference == "soft":
        return coupon_type if coupon_type in ("DRINK", "FLASH") else None
    return coupon_type
