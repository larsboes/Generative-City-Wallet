from __future__ import annotations

from spark.config import GRAPH_PREF_DECAY_DEFAULT_RATE
from spark.graph.repository import get_repository
from spark.models.api import WalletSeedItem, WalletSeedResponse
from spark.repositories.redemption import acquire_graph_event_idempotency_key

# Wallet seed signals should decay faster than interaction-driven preferences.
WALLET_SEED_DECAY_RATE = max(0.03, GRAPH_PREF_DECAY_DEFAULT_RATE)


async def apply_wallet_seed_preferences(
    *, session_id: str, seeds: list[WalletSeedItem], db_path: str | None = None
) -> WalletSeedResponse:
    """
    Apply wallet-derived category priors to graph preferences.

    Idempotency is enforced in SQLite via graph_event_log so repeated imports
    do not duplicate reinforcement events.
    """
    repo = get_repository()
    if not repo.is_available():
        return WalletSeedResponse(session_id=session_id, applied=0, skipped=len(seeds))

    applied = 0
    skipped = 0
    await repo.ensure_session(session_id)
    for seed in seeds:
        event_applied = acquire_graph_event_idempotency_key(
            event_type=f"wallet_seed:{seed.category}",
            session_id=session_id,
            offer_id=None,
            source="wallet_seed",
            db_path=db_path,
        )
        if not event_applied:
            skipped += 1
            continue

        # Base weight is intentionally conservative for cold-start priors.
        delta = max(0.0, min(seed.weight, 1.0)) * 0.35
        await repo.reinforce_category(
            session_id=session_id,
            category=seed.category,
            delta=delta,
            base_weight=0.25,
            source_type="wallet_seed",
            decay_rate=WALLET_SEED_DECAY_RATE,
        )
        applied += 1

    return WalletSeedResponse(session_id=session_id, applied=applied, skipped=skipped)
