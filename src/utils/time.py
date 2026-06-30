"""Time helpers for market-session calculations."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
BERLIN_TZ = ZoneInfo("Europe/Berlin")
NEW_YORK_TZ = ZoneInfo("America/New_York")


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(tz=UTC)


def berlin_now() -> datetime:
    """Return the current timezone-aware Berlin datetime."""
    return utc_now().astimezone(BERLIN_TZ)


def as_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
