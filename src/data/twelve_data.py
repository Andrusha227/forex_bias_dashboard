"""Optional Twelve Data adapter for EUR/USD candles and DO range."""

from __future__ import annotations

import os
from datetime import datetime
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


def get_twelve_data_ny_4h_open_range() -> Optional[Dict[str, Any]]:
    """Return first post-midnight H4 candle range for the current New York date."""
    api_key = _api_key()
    if not api_key:
        return None

    df = _fetch_time_series(
        symbol=os.getenv("TWELVE_DATA_SYMBOL", "EUR/USD"),
        interval="4h",
        outputsize=60,
        api_key=api_key,
        timezone_name="America/New_York",
    )
    if df is None or df.empty:
        return None

    return build_daily_open_range_from_h4(df, int(os.getenv("TWELVE_DATA_DO_START_HOUR_NY", "1")))


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


def build_daily_open_range_from_h4(df: pd.DataFrame, start_hour: int = 1) -> Optional[Dict[str, Any]]:
    """Build DO range from the first post-midnight NY H4 candle."""
    local = df.copy()
    local["time_ny"] = local["date"].dt.tz_convert(NEW_YORK_TZ)
    latest_ny = local.iloc[-1]["time_ny"]
    current_ny_date = latest_ny.date()
    window_end_hour = start_hour + 4
    day_candles = local[
        (local["time_ny"].dt.date == current_ny_date)
        & (local["time_ny"].dt.hour >= start_hour)
        & (local["time_ny"].dt.hour < window_end_hour)
    ]
    if day_candles.empty:
        day_candles = local[local["time_ny"].dt.date == current_ny_date]
    if day_candles.empty:
        return None

    first = day_candles.sort_values("date").iloc[0]
    return {
        "source": "twelve data",
        "daily_open": float(first["open"]),
        "daily_open_high": float(first["high"]),
        "daily_open_low": float(first["low"]),
        "latest_close": float(local.iloc[-1]["close"]),
        "candle_time_utc": first["date"].to_pydatetime(),
        "candle_time_ny": first["time_ny"].to_pydatetime(),
        "daily_open_window": (
            f"{first['time_ny'].strftime('%H:%M')} NY first post-midnight H4 candle via Twelve Data"
        ),
    }


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
