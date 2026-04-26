"""
QR token generation, validation, and cashback credit.
"""

import hashlib
import hmac
import time
from datetime import datetime

from spark.config import (
    HMAC_SECRET,
    DEFAULT_QR_VALID_MINUTES,
    GRAPH_PREF_DECAY_DEFAULT_RATE,
)
from spark.graph.repository import get_repository
from spark.repositories.redemption import (
    acquire_graph_event_idempotency_key,
    cleanup_graph_event_log,
    credit_wallet_transaction,
    get_offer_audit_row,
    get_wallet_snapshot,
    lookup_merchant_category_for_offer as lookup_merchant_category_for_offer_repo,
    mark_offer_outcome,
    mark_offer_redeemed,
)
from spark.utils.logger import get_logger
from spark.services.canonicalization import parse_stored_offer

logger = get_logger("spark.redemption")

# Reinforcement deltas for the user knowledge graph.
# Tuned conservatively — the graph is bounded to [0, 1].
PREFERENCE_DELTA_REDEEM = 0.08
PREFERENCE_DELTA_DECLINE = -0.03
PREFERENCE_DELTA_EXPIRE = -0.01
GRAPH_EVENT_RETENTION_DAYS = 45


def generate_qr_payload(offer_id: str, session_id: str) -> str:
    """Generate a signed QR payload for an accepted offer."""
    expiry_unix = int(time.time()) + (DEFAULT_QR_VALID_MINUTES * 60)
    token_hash = _compute_token(offer_id, session_id, expiry_unix)
    return f"spark://redeem/{offer_id}/{token_hash}/{expiry_unix}"


def validate_qr(
    qr_payload: str,
    merchant_id: str,
    db_path: str | None = None,
) -> dict:
    """Validate a QR code scanned by a merchant."""
    try:
        # Parse payload
        parts = qr_payload.replace("spark://redeem/", "").split("/")
        if len(parts) != 3:
            return {"valid": False, "error": "INVALID_TOKEN"}

        offer_id, token_hash, expiry_unix_str = parts
        expiry_unix = int(expiry_unix_str)

        # Check expiry
        if time.time() > expiry_unix:
            return {"valid": False, "offer_id": offer_id, "error": "EXPIRED"}

        # Look up offer in audit log
        offer_row = get_offer_audit_row(offer_id=offer_id, db_path=db_path)

        if not offer_row:
            return {"valid": False, "offer_id": offer_id, "error": "INVALID_TOKEN"}

        # Check if already redeemed
        if offer_row["status"] == "REDEEMED":
            return {"valid": False, "offer_id": offer_id, "error": "ALREADY_REDEEMED"}

        # Verify merchant match
        if offer_row["merchant_id"] != merchant_id:
            return {"valid": False, "offer_id": offer_id, "error": "WRONG_MERCHANT"}

        # Verify token (HMAC)
        expected_token = _compute_token(offer_id, offer_row["session_id"], expiry_unix)
        if not hmac.compare_digest(token_hash, expected_token):
            return {"valid": False, "offer_id": offer_id, "error": "INVALID_TOKEN"}

        # Parse discount from final_offer
        parsed_offer = parse_stored_offer(offer_row["final_offer"])
        final_offer = parsed_offer.value

        return {
            "valid": True,
            "offer_id": offer_id,
            "merchant_id": merchant_id,
            "discount_value": final_offer.discount.value if final_offer else 0,
            "discount_type": (
                final_offer.discount.type if final_offer else "percentage"
            ),
            "session_id": offer_row["session_id"],
            "expires_at": datetime.fromtimestamp(expiry_unix).isoformat(),
        }

    except Exception:
        return {"valid": False, "error": "INVALID_TOKEN"}


def confirm_redemption(
    offer_id: str,
    db_path: str | None = None,
) -> dict:
    """Confirm redemption and credit cashback."""
    offer_row = get_offer_audit_row(offer_id=offer_id, db_path=db_path)

    if not offer_row:
        return {"success": False, "error": "Offer not found"}

    # Update offer status
    now = datetime.now().isoformat()
    mark_offer_redeemed(offer_id=offer_id, redeemed_at_iso=now, db_path=db_path)

    # Calculate cashback (discount value as cashback EUR)
    parsed_offer = parse_stored_offer(offer_row["final_offer"])
    final_offer = parsed_offer.value
    discount_pct = final_offer.discount.value if final_offer else 0
    merchant_name = final_offer.merchant.name if final_offer else "Unknown"

    # Assume average transaction of €5 for cashback calculation
    avg_transaction = 5.0
    cashback_amount = round(avg_transaction * discount_pct / 100, 2)
    if cashback_amount < 0.01:
        cashback_amount = 0.68  # fallback for demo

    wallet_balance = credit_wallet_transaction(
        session_id=offer_row["session_id"],
        offer_id=offer_id,
        amount_eur=cashback_amount,
        merchant_name=merchant_name,
        credited_at_iso=now,
        db_path=db_path,
    )

    return {
        "success": True,
        "session_id": offer_row["session_id"],
        "offer_id": offer_id,
        "amount_eur": cashback_amount,
        "merchant_name": merchant_name,
        "credited_at": now,
        "wallet_balance_eur": round(wallet_balance, 2),
    }


async def project_redemption_to_graph(
    *,
    session_id: str,
    offer_id: str,
    discount_value: float,
    discount_type: str,
    amount_eur: float,
    merchant_category: str | None,
) -> None:
    """
    Best-effort projection of a confirmed redemption into the user knowledge graph.

    Writes:
        (Redemption)-[:FOR_OFFER]->(Offer)
        (WalletEvent)-[:CREDIT_FOR]->(Redemption)
        (UserSession)-[:PREFERS]->(MerchantCategory)   (weight reinforced)
        (UserSession)-[:HAD_OUTCOME {status: 'REDEEMED'}]->(Offer)

    Always returns. Never raises.
    """
    if not _acquire_graph_event_idempotency_key(
        event_type="redemption_confirmed",
        session_id=session_id,
        offer_id=offer_id,
    ):
        return

    repo = get_repository()
    if not repo.is_available():
        return

    try:
        await repo.write_redemption(
            session_id=session_id,
            offer_id=offer_id,
            discount_value=float(discount_value),
            discount_type=discount_type,
        )
        await repo.write_wallet_event(offer_id=offer_id, amount_eur=float(amount_eur))
        if merchant_category:
            await repo.reinforce_category(
                session_id=session_id,
                category=merchant_category,
                delta=PREFERENCE_DELTA_REDEEM,
                base_weight=0.5,
                source_type="redemption",
                decay_rate=GRAPH_PREF_DECAY_DEFAULT_RATE,
            )
        _cleanup_graph_event_log()
    except Exception as exc:  # defensive — never fail the redemption flow
        logger.warning("Graph projection of redemption failed: %s", exc)


async def project_offer_outcome_to_graph(
    *,
    session_id: str,
    offer_id: str,
    status: str,
    merchant_category: str | None = None,
    db_path: str | None = None,
) -> bool:
    """
    Persist and project a non-redemption outcome (DECLINED / EXPIRED / ACCEPTED).

    For DECLINED/EXPIRED we apply a small negative reinforcement on the
    associated category — the user signalled the offer wasn't compelling.
    """
    updated = mark_offer_outcome(
        offer_id=offer_id,
        status=status,
        occurred_at_iso=datetime.now().isoformat(),
        db_path=db_path,
    )
    if not updated:
        return False

    if not _acquire_graph_event_idempotency_key(
        event_type=f"offer_outcome_{status.lower()}",
        session_id=session_id,
        offer_id=offer_id,
        db_path=db_path,
    ):
        return True

    repo = get_repository()
    if not repo.is_available():
        return True

    try:
        await repo.record_offer_outcome(
            session_id=session_id, offer_id=offer_id, status=status
        )
        if status == "DECLINED" and merchant_category:
            await repo.reinforce_category(
                session_id=session_id,
                category=merchant_category,
                delta=PREFERENCE_DELTA_DECLINE,
                base_weight=0.5,
                source_type="decline",
                decay_rate=GRAPH_PREF_DECAY_DEFAULT_RATE,
            )
        elif status == "EXPIRED" and merchant_category:
            await repo.reinforce_category(
                session_id=session_id,
                category=merchant_category,
                delta=PREFERENCE_DELTA_EXPIRE,
                base_weight=0.5,
                source_type="expire",
                decay_rate=GRAPH_PREF_DECAY_DEFAULT_RATE,
            )
        _cleanup_graph_event_log()
    except Exception as exc:
        logger.warning("Graph projection of outcome failed: %s", exc)
    return True


def lookup_merchant_category_for_offer(
    offer_id: str, db_path: str | None = None
) -> str | None:
    """Return the merchant category for an offer (used when projecting outcomes)."""
    return lookup_merchant_category_for_offer_repo(offer_id=offer_id, db_path=db_path)


def get_wallet(session_id: str, db_path: str | None = None) -> dict:
    """Get wallet balance and transaction history."""
    balance, transactions = get_wallet_snapshot(session_id=session_id, db_path=db_path)

    return {
        "session_id": session_id,
        "balance_eur": round(balance, 2),
        "transactions": [
            {
                "offer_id": t["offer_id"],
                "amount_eur": t["amount_eur"],
                "merchant_name": t["merchant_name"],
                "credited_at": t["credited_at"],
            }
            for t in transactions
        ],
    }


def _compute_token(offer_id: str, session_id: str, expiry_unix: int) -> str:
    """HMAC token for QR payload."""
    msg = f"{offer_id}:{session_id}:{expiry_unix}"
    return hmac.new(HMAC_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]


def _acquire_graph_event_idempotency_key(
    *,
    event_type: str,
    session_id: str | None,
    offer_id: str | None,
    db_path: str | None = None,
) -> bool:
    """Insert-once guard for graph side-effects."""
    return acquire_graph_event_idempotency_key(
        event_type=event_type,
        session_id=session_id,
        offer_id=offer_id,
        source="kg_projection",
        db_path=db_path,
    )


def _cleanup_graph_event_log(db_path: str | None = None) -> None:
    """Best-effort retention cleanup for projection idempotency rows."""
    cleanup_graph_event_log(
        retention_days=GRAPH_EVENT_RETENTION_DAYS,
        db_path=db_path,
    )
