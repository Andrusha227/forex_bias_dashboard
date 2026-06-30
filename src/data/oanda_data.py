"""Optional OANDA candle adapter for NY-aligned 4H Daily Open range."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from src.utils.time import NEW_YORK_TZ, as_utc


OANDA_PRACTICE_URL = "https://api-fxpractice.oanda.com"
OANDA_LIVE_URL = "https://api-fxtrade.oanda.com"


def get_oanda_ny_4h_open_range() -> Optional[Dict[str, Any]]:
    """Return the first H4 candle range for the current New York trading day."""
    load_dotenv()
    token = os.getenv("OANDA_API_TOKEN")
    if not token:
        return None

    instrument = os.getenv("OANDA_INSTRUMENT", "EUR_USD")
    environment = os.getenv("OANDA_ENVIRONMENT", "practice").lower()
    base_url = OANDA_LIVE_URL if environment == "live" else OANDA_PRACTICE_URL
    alignment_hour = int(os.getenv("OANDA_DAILY_ALIGNMENT_HOUR_NY", "17"))

    try:
        candles = _fetch_h4_candles(base_url, token, instrument, alignment_hour)
        if not candles:
            return None
        return _first_candle_for_current_ny_trading_day(candles, instrument, alignment_hour, environment)
    except Exception:
        return None


def _fetch_h4_candles(base_url: str, token: str, instrument: str, alignment_hour: int) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{base_url}/v3/instruments/{instrument}/candles",
        params={
            "price": "M",
            "granularity": "H4",
            "count": 30,
            "smooth": "false",
            "dailyAlignment": alignment_hour,
            "alignmentTimezone": "America/New_York",
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("candles", [])


def _first_candle_for_current_ny_trading_day(
    candles: List[Dict[str, Any]],
    instrument: str,
    alignment_hour: int,
    environment: str,
) -> Optional[Dict[str, Any]]:
    parsed = []
    for candle in candles:
        mid = candle.get("mid") or {}
        if not mid:
            continue
        time_utc = as_utc(_parse_oanda_time(candle["time"]))
        parsed.append(
            {
                "time_utc": time_utc,
                "time_ny": time_utc.astimezone(NEW_YORK_TZ),
                "open": float(mid["o"]),
                "high": float(mid["h"]),
                "low": float(mid["l"]),
                "close": float(mid["c"]),
                "complete": bool(candle.get("complete")),
            }
        )

    if not parsed:
        return None

    latest_ny = parsed[-1]["time_ny"]
    trading_day = _ny_trading_day(latest_ny, alignment_hour)
    day_candles = [candle for candle in parsed if _ny_trading_day(candle["time_ny"], alignment_hour) == trading_day]
    if not day_candles:
        return None

    first = sorted(day_candles, key=lambda candle: candle["time_utc"])[0]
    return {
        "instrument": instrument,
        "environment": environment,
        "source": "oanda",
        "daily_open": first["open"],
        "daily_open_high": first["high"],
        "daily_open_low": first["low"],
        "latest_close": parsed[-1]["close"],
        "candle_time_utc": first["time_utc"],
        "candle_time_ny": first["time_ny"],
        "daily_open_window": (
            f"{first['time_ny'].strftime('%H:%M')} NY first H4 candle "
            f"({first['time_utc'].astimezone().strftime('%H:%M %Z')})"
        ),
    }


def _ny_trading_day(value: datetime, alignment_hour: int) -> date:
    """Map a NY timestamp to the trading day that starts at alignment_hour."""
    if value.hour >= alignment_hour:
        return value.date() + timedelta(days=1)
    return value.date()


def _parse_oanda_time(value: str) -> datetime:
    """Parse OANDA RFC3339 timestamps, truncating nanoseconds to microseconds."""
    normalized = value.replace("Z", "+00:00")
    if "." not in normalized:
        return datetime.fromisoformat(normalized)
    prefix, suffix = normalized.split(".", 1)
    timezone_index = max(suffix.find("+"), suffix.find("-"))
    if timezone_index == -1:
        fraction = suffix[:6].ljust(6, "0")
        timezone_part = ""
    else:
        fraction = suffix[:timezone_index][:6].ljust(6, "0")
        timezone_part = suffix[timezone_index:]
    return datetime.fromisoformat(f"{prefix}.{fraction}{timezone_part}")
