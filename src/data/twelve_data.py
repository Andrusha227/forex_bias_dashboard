"""Optional Twelve Data adapter for EUR/USD candles and weekly open ranges."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils.time import NEW_YORK_TZ


TWELVE_DATA_TIME_SERIES_URL = "https://api.twelvedata.com/time_series"


def get_twelve_data_eurusd_daily(days: int = 160) -> Optional[pd.DataFrame]:
    """Return EUR/USD daily candles from Twelve Data if configured."""
    api_key = _api_key()
    if not api_key:
        return None
    return _fetch_time_series(symbol="EUR/USD", interval="1day", outputsize=days, api_key=api_key, timezone_name="UTC")


def get_twelve_data_eurusd_h4(outputsize: int = 120) -> Optional[pd.DataFrame]:
    """Return EUR/USD H4 candles in New York timezone alignment."""
    api_key = _api_key()
    if not api_key:
        return None
    return _fetch_time_series(
        symbol=os.getenv("TWELVE_DATA_SYMBOL", "EUR/USD"),
        interval="4h",
        outputsize=outputsize,
        api_key=api_key,
        timezone_name="America/New_York",
    )


def build_weekly_open_ranges_from_h4(df: pd.DataFrame) -> Dict[str, Optional[Dict[str, Any]]]:
    """Build Sunday open and Monday first post-midnight H4 ranges."""
    local = df.copy()
    local["time_ny"] = local["date"].dt.tz_convert(NEW_YORK_TZ)
    latest_ny = local.iloc[-1]["time_ny"]
    week_start = pd.Timestamp(latest_ny.date()) - pd.Timedelta(days=latest_ny.weekday())
    week_start = week_start.tz_localize(NEW_YORK_TZ)
    sunday_session_start = week_start - pd.Timedelta(hours=7)

    sunday = local[(local["time_ny"] >= sunday_session_start) & (local["time_ny"] < week_start)].sort_values("date")
    monday = local[
        (local["time_ny"].dt.date == week_start.date())
        & (local["time_ny"].dt.hour >= 1)
        & (local["time_ny"].dt.hour < 5)
    ].sort_values("date")

    return {
        "sunday_open": _range_from_first_row(sunday, "Sunday session weekly open range"),
        "monday_open": _range_from_first_row(monday, "Monday 01:00 NY first H4 weekly range"),
    }


def _range_from_first_row(frame: pd.DataFrame, label: str) -> Optional[Dict[str, Any]]:
    if frame.empty:
        return None
    first = frame.iloc[0]
    return {
        "source": "twelve data",
        "open": float(first["open"]),
        "high": float(first["high"]),
        "low": float(first["low"]),
        "time_utc": first["date"].to_pydatetime(),
        "time_ny": first["time_ny"].to_pydatetime(),
        "label": f"{label} ({first['time_ny'].strftime('%a %H:%M')} NY)",
    }


def _api_key() -> Optional[str]:
    load_dotenv()
    key = os.getenv("TWELVE_DATA_API_KEY")
    return key.strip() if key else None


def _fetch_time_series(
    symbol: str,
    interval: str,
    outputsize: int,
    api_key: str,
    timezone_name: str,
) -> Optional[pd.DataFrame]:
    response = requests.get(
        TWELVE_DATA_TIME_SERIES_URL,
        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "timezone": timezone_name,
            "apikey": api_key,
            "format": "JSON",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") == "error":
        raise ValueError(payload.get("message", "Twelve Data returned an error"))

    values: List[Dict[str, Any]] = payload.get("values", [])
    if not values:
        return None

    rows = []
    for item in values:
        dt = pd.Timestamp(item["datetime"])
        if dt.tzinfo is None:
            dt = dt.tz_localize(timezone_name)
        rows.append(
            {
                "date": dt.tz_convert("UTC"),
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume", 0) or 0),
            }
        )

    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
