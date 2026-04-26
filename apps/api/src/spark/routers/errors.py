from __future__ import annotations

from fastapi import HTTPException


def as_not_found(exc: LookupError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def as_bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))
