"""Market data adapters for EUR/USD and DXY — no mock fallback."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests

from src.data.twelve_data import (
    build_weekly_open_ranges_from_h4,
    get_twelve_data_eurusd_daily,
    get_twelve_data_eurusd_h4,
)


STOOQ_DAILY_URL = "https://stooq.com/q/d/l/"


def fetch_stooq_daily(symbol: str, days: int = 120) -> Tuple[Optional[pd.DataFrame], str]:
    """Fetch daily OHLC data from Stooq.

    Returns (DataFrame, 'stooq') on success or (None, 'unavailable') on failure.
    """
    try:
        response = requests.get(
            STOOQ_DAILY_URL,
            params={"s": symbol, "i": "d"},
            timeout=8,
            headers={"User-Agent": "forex_bias_dashboard/0.1"},
        )
        response.raise_for_status()
        if "Date" not in response.text:
            raise ValueError("Stooq response did not contain OHLC data")

        from io import StringIO

        df = pd.read_csv(StringIO(response.text))
        df.columns = [column.lower() for column in df.columns]
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").tail(days).reset_index(drop=True)
        if df.empty:
            raise ValueError("Stooq returned no rows")
        return df, "stooq"
    except Exception:
        return None, "unavailable"


def get_eurusd_snapshot() -> Optional[Dict[str, Any]]:
    """Return EUR/USD levels needed by monthly, weekly, and daily sections.

    Returns None if both Twelve Data and Stooq fail (no data at all).
    """
    twelve_daily = get_twelve_data_eurusd_daily(days=160)
    if twelve_daily is not None and not twelve_daily.empty:
        df, source = twelve_daily, "twelve data"
    else:
        df, source = fetch_stooq_daily("eurusd", days=160)

    if df is None:
        return None

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest

    current_price = float(latest["close"])
    h4 = get_twelve_data_eurusd_h4(outputsize=120)
    weekly_open_ranges = build_weekly_open_ranges_from_h4(h4) if h4 is not None and not h4.empty else {}

    # If H4 data is available, prefer its latest close for current price
    if h4 is not None and not h4.empty:
        current_price = float(h4.iloc[-1]["close"])

    dated = df.copy()
    dated["session_date"] = dated["date"].dt.tz_convert(None)
    latest_date = pd.Timestamp(dated.iloc[-1]["session_date"])

    month_rows = dated[dated["session_date"].dt.to_period("M") == latest_date.to_period("M")]
    week_start = latest_date.normalize() - pd.Timedelta(days=latest_date.weekday())
    week_rows = dated[dated["session_date"] >= week_start]
    previous_week_rows = dated[
        (dated["session_date"] >= week_start - pd.Timedelta(days=7)) & (dated["session_date"] < week_start)
    ]

    # Calculate Monthly open ranges
    monthly_open_ranges = {}
    if not month_rows.empty:
        first_trade = month_rows.iloc[0]
        d_open = float(first_trade["open"])
        d_high = float(first_trade["high"])
        d_low = float(first_trade["low"])
        d_time_utc = first_trade["date"]
        first_trade_date = first_trade["session_date"]

        first_week_start = first_trade_date - pd.Timedelta(days=first_trade_date.weekday())
        first_week_end = first_week_start + pd.Timedelta(days=6)
        first_week_rows = dated[(dated["session_date"] >= first_week_start) & (dated["session_date"] <= first_week_end)]

        if not first_week_rows.empty:
            w_open = float(first_week_rows.iloc[0]["open"])
            w_high = float(first_week_rows["high"].max())
            w_low = float(first_week_rows["low"].min())
            w_time_utc = first_week_rows.iloc[0]["date"]
        else:
            w_open, w_high, w_low, w_time_utc = d_open, d_high, d_low, d_time_utc

        first_week_subsequent = first_week_rows[first_week_rows["session_date"] > first_trade_date]
        d_swept_during_first_week = False
        if not first_week_subsequent.empty:
            d_swept_high = float(first_week_subsequent["high"].max()) > d_high
            d_swept_low = float(first_week_subsequent["low"].min()) < d_low
            d_swept_during_first_week = d_swept_high or d_swept_low

        is_after_first_week = latest_date > first_week_end
        active_source = "W" if (is_after_first_week and d_swept_during_first_week) else "D"

        monthly_open_ranges = {
            "d_open": {
                "open": d_open,
                "high": d_high,
                "low": d_low,
                "time_utc": d_time_utc,
                "label": "First Day of Month (D)"
            },
            "w_open": {
                "open": w_open,
                "high": w_high,
                "low": w_low,
                "time_utc": w_time_utc,
                "label": "First Week of Month (W)"
            },
            "d_swept_during_first_week": d_swept_during_first_week,
            "is_after_first_week": is_after_first_week,
            "active_source": active_source
        }
    else:
        monthly_open = float(latest["open"])
        monthly_open_ranges = {
            "d_open": {
                "open": monthly_open,
                "high": monthly_open,
                "low": monthly_open,
                "time_utc": latest["date"],
                "label": "First Day of Month (D)"
            },
            "w_open": {
                "open": monthly_open,
                "high": monthly_open,
                "low": monthly_open,
                "time_utc": latest["date"],
                "label": "First Week of Month (W)"
            },
            "d_swept_during_first_week": False,
            "is_after_first_week": False,
            "active_source": "D"
        }

    # Calculate Weekly Open Dynamic Transition (Monday 4H vs Monday Daily)
    monday_d = None
    monday_4h_swept = False
    monday_daily_rows = dated[dated["session_date"] == week_start]

    if not monday_daily_rows.empty:
        first_row = monday_daily_rows.iloc[0]
        monday_d = {
            "open": float(first_row["open"]),
            "high": float(first_row["high"]),
            "low": float(first_row["low"]),
            "time_utc": first_row["date"],
            "label": "Monday Daily Candle (D)"
        }

        monday_4h = weekly_open_ranges.get("monday_open")
        if monday_4h:
            monday_4h_high = float(monday_4h["high"])
            monday_4h_low = float(monday_4h["low"])
            monday_d_high = float(first_row["high"])
            monday_d_low = float(first_row["low"])
            # Check if daily high/low exceeded 4H high/low on Monday
            monday_4h_swept = (monday_d_high > monday_4h_high) or (monday_d_low < monday_4h_low)

    is_after_monday = latest_date > week_start
    active_weekly_source = "D" if (is_after_monday and not monday_4h_swept) else "4H"

    weekly_open_ranges["monday_d"] = monday_d
    weekly_open_ranges["monday_4h_swept"] = monday_4h_swept
    weekly_open_ranges["is_after_monday"] = is_after_monday
    weekly_open_ranges["active_source"] = active_weekly_source

    weekly_open = float(week_rows.iloc[0]["open"]) if not week_rows.empty else float(latest["open"])

    # Freshness calculation
    from datetime import datetime, timezone
    try:
        latest_date = df.iloc[-1]["date"]
        if latest_date.tzinfo is not None:
            age_days = (datetime.now(timezone.utc) - latest_date).days
        else:
            age_days = (datetime.now().date() - latest_date.date()).days
        freshness = "fresh" if age_days <= 4 else "stale"
        timestamp = latest_date.strftime("%Y-%m-%d")
    except Exception:
        freshness = "unknown"
        timestamp = "n/a"

    monthly_open_ranges["freshness"] = freshness
    monthly_open_ranges["timestamp"] = timestamp
    weekly_open_ranges["freshness"] = freshness
    weekly_open_ranges["timestamp"] = timestamp

    return {
        "source": source,
        "current_price": current_price,
        "monthly_open": float(month_rows.iloc[0]["open"]) if not month_rows.empty else float(latest["open"]),
        "monthly_open_ranges": monthly_open_ranges,
        "weekly_open": weekly_open,
        "weekly_open_ranges": weekly_open_ranges,
        "previous_week_high": float(previous_week_rows["high"].max()) if not previous_week_rows.empty else float(previous["high"]),
        "previous_week_low": float(previous_week_rows["low"].min()) if not previous_week_rows.empty else float(previous["low"]),
        "yesterday_high": float(previous["high"]),
        "yesterday_low": float(previous["low"]),
        "history": df,
        "h4_history": h4,
        "timestamp": timestamp,
        "freshness": freshness,
    }


def get_dxy_direction() -> Optional[Dict[str, Any]]:
    """Return DXY direction using Stooq. Returns None when data is unavailable."""
    df, source = fetch_stooq_daily("dx.f", days=30)
    if df is None:
        return None
    if len(df) < 6:
        return {"source": source, "direction": "flat", "latest": None, "previous": None, "timestamp": "n/a", "freshness": "unknown"}

    latest = float(df.iloc[-1]["close"])
    previous = float(df.iloc[-6]["close"])
    direction = _direction(latest, previous)

    # Freshness calculation
    from datetime import datetime, timezone
    try:
        latest_date = df.iloc[-1]["date"]
        if latest_date.tzinfo is not None:
            age_days = (datetime.now(timezone.utc) - latest_date).days
        else:
            age_days = (datetime.now().date() - latest_date.date()).days
        freshness = "fresh" if age_days <= 4 else "stale"
        timestamp = latest_date.strftime("%Y-%m-%d")
    except Exception:
        freshness = "unknown"
        timestamp = "n/a"

    return {
        "source": source,
        "direction": direction,
        "latest": latest,
        "previous": previous,
        "timestamp": timestamp,
        "freshness": freshness,
    }


def _direction(latest: float, previous: float) -> str:
    if latest > previous:
        return "rising"
    if latest < previous:
        return "falling"
    return "flat"
