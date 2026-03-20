from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def round2(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None