from __future__ import annotations

from fastapi import Header, HTTPException

from spark.config import ADMIN_SECRET


def as_not_found(exc: LookupError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def as_bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def require_admin(x_admin_secret: str = Header(default="")) -> None:
    """Dependency that enforces SPARK_ADMIN_SECRET when one is configured."""
    if ADMIN_SECRET and x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
