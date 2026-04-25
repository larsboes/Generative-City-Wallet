"""
QR token generation, validation, and cashback credit.
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime

from src.backend.config import (
    HMAC_SECRET,
    DEFAULT_QR_VALID_MINUTES,
    GRAPH_PREF_DECAY_DEFAULT_RATE,
)
from src.backend.db.connection import get_connection
from src.backend.graph.repository import get_repository

logger = logging.getLogger("spark.redemption")

# Reinforcement deltas for the user knowledge graph.
# Tuned conservatively — the graph is bounded to [0, 1].
PREFERENCE_DELTA_REDEEM = 0.08
PREFERENCE_DELTA_DECLINE = -0.03
PREFERENCE_DELTA_EXPIRE = -0.01


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
        conn = get_connection(db_path)
        offer_row = conn.execute(
            "SELECT * FROM offer_audit_log WHERE offer_id = ?",
            (offer_id,),
        ).fetchone()

        if not offer_row:
            conn.close()
            return {"valid": False, "offer_id": offer_id, "error": "INVALID_TOKEN"}

        # Check if already redeemed
        if offer_row["status"] == "REDEEMED":
            conn.close()
            return {"valid": False, "offer_id": offer_id, "error": "ALREADY_REDEEMED"}

        # Verify merchant match
        if offer_row["merchant_id"] != merchant_id:
            conn.close()
            return {"valid": False, "offer_id": offer_id, "error": "WRONG_MERCHANT"}

        # Verify token (HMAC)
        expected_token = _compute_token(offer_id, offer_row["session_id"], expiry_unix)
        if not hmac.compare_digest(token_hash, expected_token):
            conn.close()
            return {"valid": False, "offer_id": offer_id, "error": "INVALID_TOKEN"}

        # Parse discount from final_offer
        final_offer = (
            json.loads(offer_row["final_offer"]) if offer_row["final_offer"] else {}
        )
        discount = final_offer.get("discount", {})

        conn.close()

        return {
            "valid": True,
            "offer_id": offer_id,
            "merchant_id": merchant_id,
            "discount_value": discount.get("value", 0),
            "discount_type": discount.get("type", "percentage"),
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
    conn = get_connection(db_path)

    offer_row = conn.execute(
        "SELECT * FROM offer_audit_log WHERE offer_id = ?",
        (offer_id,),
    ).fetchone()

    if not offer_row:
        conn.close()
        return {"success": False, "error": "Offer not found"}

    # Update offer status
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE offer_audit_log SET status = 'REDEEMED', redeemed_at = ? WHERE offer_id = ?",
        (now, offer_id),
    )

    # Calculate cashback (discount value as cashback EUR)
    final_offer = (
        json.loads(offer_row["final_offer"]) if offer_row["final_offer"] else {}
    )
    discount = final_offer.get("discount", {})
    discount_pct = discount.get("value", 0)
    merchant_name = final_offer.get("merchant", {}).get("name", "Unknown")

    # Assume average transaction of €5 for cashback calculation
    avg_transaction = 5.0
    cashback_amount = round(avg_transaction * discount_pct / 100, 2)
    if cashback_amount < 0.01:
        cashback_amount = 0.68  # fallback for demo

    # Credit wallet
    conn.execute(
        "INSERT INTO wallet_transactions (session_id, offer_id, amount_eur, merchant_name, credited_at) VALUES (?, ?, ?, ?, ?)",
        (offer_row["session_id"], offer_id, cashback_amount, merchant_name, now),
    )

    # Compute new balance
    balance_row = conn.execute(
        "SELECT COALESCE(SUM(amount_eur), 0) as total FROM wallet_transactions WHERE session_id = ?",
        (offer_row["session_id"],),
    ).fetchone()

    conn.commit()
    conn.close()

    return {
        "success": True,
        "session_id": offer_row["session_id"],
        "offer_id": offer_id,
        "amount_eur": cashback_amount,
        "merchant_name": merchant_name,
        "credited_at": now,
        "wallet_balance_eur": round(balance_row["total"], 2),
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
    except Exception as exc:  # defensive — never fail the redemption flow
        logger.warning("Graph projection of redemption failed: %s", exc)


async def project_offer_outcome_to_graph(
    *,
    session_id: str,
    offer_id: str,
    status: str,
    merchant_category: str | None = None,
) -> None:
    """
    Project a non-redemption outcome (DECLINED / EXPIRED / ACCEPTED) into the graph.

    For DECLINED/EXPIRED we apply a small negative reinforcement on the
    associated category — the user signalled the offer wasn't compelling.
    """
    repo = get_repository()
    if not repo.is_available():
        return

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
    except Exception as exc:
        logger.warning("Graph projection of outcome failed: %s", exc)


def lookup_merchant_category_for_offer(
    offer_id: str, db_path: str | None = None
) -> str | None:
    """Return the merchant category for an offer (used when projecting outcomes)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT m.type AS category
            FROM offer_audit_log o
            JOIN merchants m ON m.id = o.merchant_id
            WHERE o.offer_id = ?
            """,
            (offer_id,),
        ).fetchone()
        return row["category"] if row else None
    finally:
        conn.close()


def get_wallet(session_id: str, db_path: str | None = None) -> dict:
    """Get wallet balance and transaction history."""
    conn = get_connection(db_path)

    balance_row = conn.execute(
        "SELECT COALESCE(SUM(amount_eur), 0) as total FROM wallet_transactions WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    transactions = conn.execute(
        "SELECT offer_id, amount_eur, merchant_name, credited_at FROM wallet_transactions WHERE session_id = ? ORDER BY credited_at DESC LIMIT 20",
        (session_id,),
    ).fetchall()

    conn.close()

    return {
        "session_id": session_id,
        "balance_eur": round(balance_row["total"], 2),
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
