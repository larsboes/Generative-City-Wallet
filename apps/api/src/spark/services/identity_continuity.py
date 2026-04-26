from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from spark.config import HMAC_SECRET
from spark.repositories.redemption import acquire_graph_event_idempotency_key

CONTINUITY_RETENTION_DAYS = 30


@dataclass(frozen=True)
class ContinuityIdentity:
    continuity_id: str
    source: str
    expires_at_iso: str


@dataclass(frozen=True)
class ContinuityResetResult:
    session_id: str
    continuity_id: str | None
    continuity_hint: str | None
    source: str
    expires_at_iso: str
    reset_applied: bool
    opt_out: bool


def resolve_continuity_identity(
    *,
    session_id: str,
    continuity_hint: str | None,
    now: datetime | None = None,
) -> ContinuityIdentity:
    ts = now or datetime.now(timezone.utc)
    identity_source = "hinted_pseudonym" if continuity_hint else "session_fallback"
    seed_value = continuity_hint.strip() if continuity_hint else session_id
    digest = hmac.new(
        HMAC_SECRET.encode("utf-8"),
        f"continuity:{seed_value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
    expires = ts + timedelta(days=CONTINUITY_RETENTION_DAYS)
    return ContinuityIdentity(
        continuity_id=f"cid_{digest}",
        source=identity_source,
        expires_at_iso=expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )


def reset_continuity_identity(
    *,
    session_id: str,
    continuity_hint: str | None,
    opt_out: bool = False,
    now: datetime | None = None,
    db_path: str | None = None,
) -> ContinuityResetResult:
    ts = now or datetime.now(timezone.utc)
    if opt_out:
        event_applied = acquire_graph_event_idempotency_key(
            event_type="continuity_reset:opt_out",
            session_id=session_id,
            offer_id=None,
            source="identity_continuity",
            category=None,
            source_event_id=None,
            payload={"opt_out": True},
            event_unix=ts.timestamp(),
            db_path=db_path,
        )
        expires = ts + timedelta(days=CONTINUITY_RETENTION_DAYS)
        return ContinuityResetResult(
            session_id=session_id,
            continuity_id=None,
            continuity_hint=None,
            source="opt_out",
            expires_at_iso=expires.replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            reset_applied=event_applied,
            opt_out=True,
        )

    new_hint = f"hint_{secrets.token_urlsafe(12)}"
    identity = resolve_continuity_identity(
        session_id=session_id,
        continuity_hint=new_hint,
        now=ts,
    )
    event_applied = acquire_graph_event_idempotency_key(
        event_type="continuity_reset:rotate",
        session_id=session_id,
        offer_id=None,
        source="identity_continuity",
        category=None,
        source_event_id=None,
        payload={
            "previous_hint_present": bool(continuity_hint),
            "new_continuity_id": identity.continuity_id,
        },
        event_unix=ts.timestamp(),
        db_path=db_path,
    )
    return ContinuityResetResult(
        session_id=session_id,
        continuity_id=identity.continuity_id,
        continuity_hint=new_hint,
        source=identity.source,
        expires_at_iso=identity.expires_at_iso,
        reset_applied=event_applied,
        opt_out=False,
    )
