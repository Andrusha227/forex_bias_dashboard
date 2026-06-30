"""Market data adapters for EUR/USD and DXY with mock fallback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests

from src.data.oanda_data import get_oanda_ny_4h_open_range
from src.data.twelve_data import (
    build_daily_open_range_from_h4,
    build_weekly_open_ranges_from_h4,
    get_twelve_data_eurusd_daily,
    get_twelve_data_eurusd_h4,
    get_twelve_data_ny_4h_open_range,
)
from src.utils.time import BERLIN_TZ


STOOQ_DAILY_URL = "https://stooq.com/q/d/l/"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
EURUSD_NY_4H_OPEN_LOCAL_HOUR = 1
EURUSD_NY_4H_OPEN_WINDOW_HOURS = 4


def fetch_stooq_daily(symbol: str, days: int = 120) -> Tuple[pd.DataFrame, str]:
    """Fetch daily OHLC data from Stooq, falling back to deterministic mock data."""
    try:
        response = requests.get(
            STOOQ_DAILY_URL,
            params={"s": symbol, "i": "d"},
            timeout=8,
            headers={"User-Agent": "eurusd-bias-dashboard/0.1"},
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
        return _mock_daily(symbol=symbol, days=days), "mock"


def get_eurusd_snapshot() -> Dict[str, Any]:
    """Return EUR/USD levels needed by monthly, weekly, and intraday sections."""
    twelve_daily = get_twelve_data_eurusd_daily(days=160)
    if twelve_daily is not None and not twelve_daily.empty:
        df, source = twelve_daily, "twelve data"
    else:
        df, source = fetch_stooq_daily("eurusd", days=160)

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest

    current_price = float(latest["close"])
    h4 = get_twelve_data_eurusd_h4(outputsize=120)
    intraday = fetch_yahoo_intraday("EURUSD=X")
    twelve_context = build_daily_open_range_from_h4(h4) if h4 is not None and not h4.empty else get_twelve_data_ny_4h_open_range()
    weekly_open_ranges = build_weekly_open_ranges_from_h4(h4) if h4 is not None and not h4.empty else {}
    oanda_context = None if twelve_context is not None else get_oanda_ny_4h_open_range()

    if twelve_context is not None:
        current_price = float(twelve_context["latest_close"])
    elif oanda_context is not None:
        current_price = float(oanda_context["latest_close"])
    elif intraday is not None and not intraday.empty:
        current_price = float(intraday.iloc[-1]["close"])

    dated = df.copy()
    dated["session_date"] = dated["date"].dt.tz_convert(None)
    latest_date = pd.Timestamp(dated.iloc[-1]["session_date"])

    month_rows = dated[dated["session_date"].dt.to_period("M") == latest_date.to_period("M")]
    week_start = latest_date.normalize() - pd.Timedelta(days=latest_date.weekday())
    week_rows = dated[dated["session_date"] >= week_start]
    previous_week_rows = dated[
        (dated["session_date"] >= week_start - pd.Timedelta(days=7)) & (dated["session_date"] < week_start)
    ]

    daily_open_context = twelve_context or oanda_context or _ny_4h_daily_open(intraday)
    if daily_open_context is None:
        daily_open = float(latest["open"])
        daily_open_high = None
        daily_open_low = None
        daily_open_source = source
        daily_open_window = "Daily OHLC fallback"
        daily_open_time_utc = None
    else:
        daily_open = daily_open_context.get("daily_open", daily_open_context.get("open"))
        daily_open_high = daily_open_context.get("daily_open_high")
        daily_open_low = daily_open_context.get("daily_open_low")
        daily_open_source = daily_open_context["source"]
        daily_open_window = daily_open_context.get("daily_open_window", daily_open_context.get("window"))
        daily_open_time_utc = daily_open_context.get("candle_time_utc") or daily_open_context.get("time_utc")

    daily_range = max(float(latest["high"] - latest["low"]), 0.0010)
    asia_high = round(daily_open + daily_range * 0.35, 5)
    asia_low = round(daily_open - daily_range * 0.30, 5)

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
        monthly_open_ranges = {
            "d_open": {
                "open": daily_open,
                "high": daily_open,
                "low": daily_open,
                "time_utc": latest["date"],
                "label": "First Day of Month (D)"
            },
            "w_open": {
                "open": daily_open,
                "high": daily_open,
                "low": daily_open,
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

    return {
        "source": source,
        "current_price": current_price,
        "monthly_open": float(month_rows.iloc[0]["open"]) if not month_rows.empty else daily_open,
        "monthly_open_ranges": monthly_open_ranges,
        "weekly_open": float(week_rows.iloc[0]["open"]) if not week_rows.empty else daily_open,
        "weekly_open_ranges": weekly_open_ranges,
        "previous_week_high": float(previous_week_rows["high"].max()) if not previous_week_rows.empty else float(previous["high"]),
        "previous_week_low": float(previous_week_rows["low"].min()) if not previous_week_rows.empty else float(previous["low"]),
        "daily_open": daily_open,
        "daily_open_high": daily_open_high,
        "daily_open_low": daily_open_low,
        "daily_open_source": daily_open_source,
        "daily_open_window": daily_open_window,
        "daily_open_time_utc": daily_open_time_utc,
        "yesterday_high": float(previous["high"]),
        "yesterday_low": float(previous["low"]),
        "asia_high": asia_high,
        "asia_low": asia_low,
        "london_open": round(daily_open + daily_range * 0.08, 5),
        "new_york_open": round(daily_open - daily_range * 0.05, 5),
        "history": df,
        "h4_history": h4,
    }


def fetch_yahoo_intraday(symbol: str, interval: str = "1h", range_value: str = "5d") -> Optional[pd.DataFrame]:
    """Fetch intraday OHLC data from Yahoo chart API.

    This is best-effort only. Yahoo can rate-limit unauthenticated requests, so
    callers must always support a fallback.
    """
    try:
        response = requests.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={"interval": interval, "range": range_value},
            timeout=8,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        if not timestamps or not quote:
            raise ValueError("Yahoo returned no intraday candles")

        rows = []
        for index, timestamp in enumerate(timestamps):
            close = quote.get("close", [None])[index]
            open_price = quote.get("open", [None])[index]
            high = quote.get("high", [None])[index]
            low = quote.get("low", [None])[index]
            if open_price is None or close is None:
                continue
            rows.append(
                {
                    "date": pd.Timestamp(datetime.fromtimestamp(timestamp, tz=timezone.utc)),
                    "open": float(open_price),
                    "high": float(high) if high is not None else float(open_price),
                    "low": float(low) if low is not None else float(open_price),
                    "close": float(close),
                }
            )

        intraday = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        if intraday.empty:
            raise ValueError("Yahoo intraday frame is empty")
        return intraday
    except Exception:
        return None


def _ny_4h_daily_open(intraday: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """Return open of the first EUR/USD 4H candle in the Berlin 01:00-04:00 window."""
    if intraday is None or intraday.empty:
        return None

    local = intraday.copy()
    local["local_time"] = local["date"].dt.tz_convert(BERLIN_TZ)
    current_local_date = local.iloc[-1]["local_time"].date()
    start = pd.Timestamp(
        datetime(
            current_local_date.year,
            current_local_date.month,
            current_local_date.day,
            EURUSD_NY_4H_OPEN_LOCAL_HOUR,
            tzinfo=BERLIN_TZ,
        )
    )
    end = start + pd.Timedelta(hours=EURUSD_NY_4H_OPEN_WINDOW_HOURS)
    window = local[(local["local_time"] >= start) & (local["local_time"] < end)]
    if window.empty:
        return None

    opening_candle = window.iloc[0]
    return {
        "daily_open": float(opening_candle["open"]),
        "daily_open_high": float(window["high"].max()),
        "daily_open_low": float(window["low"].min()),
        "source": "yahoo intraday",
        "daily_open_window": (
            f"{start.strftime('%H:%M')}-{(end - pd.Timedelta(hours=1)).strftime('%H:%M')} "
            f"{start.strftime('%Z')} NY 4H open"
        ),
    }


def get_dxy_direction() -> Dict[str, Any]:
    """Return DXY direction using Stooq when available, otherwise mock data."""
    df, source = fetch_stooq_daily("dx.f", days=30)
    if len(df) < 6:
        return {"source": source, "direction": "flat", "latest": None, "previous": None}

    latest = float(df.iloc[-1]["close"])
    previous = float(df.iloc[-6]["close"])
    direction = _direction(latest, previous)
    return {"source": source, "direction": direction, "latest": latest, "previous": previous}


def _direction(latest: float, previous: float) -> str:
    if latest > previous:
        return "rising"
    if latest < previous:
        return "falling"
    return "flat"


def _mock_daily(symbol: str, days: int) -> pd.DataFrame:
    """Build deterministic OHLC data so the app works without market APIs."""
    end = datetime.now(tz=timezone.utc).date()
    dates = pd.bdate_range(end=end, periods=days, tz="UTC")

    symbol_lower = symbol.lower()
    base = 1.0830 if "eur" in symbol_lower else 104.20
    step = 0.00025 if "eur" in symbol_lower else -0.035
    amplitude = 0.0030 if "eur" in symbol_lower else 0.45

    rows = []
    for index, date in enumerate(dates):
        drift = step * index
        wave = amplitude * ((index % 10) - 5) / 10
        open_price = base + drift + wave
        close = open_price + (step * 1.5)
        high = max(open_price, close) + abs(amplitude) * 0.35
        low = min(open_price, close) - abs(amplitude) * 0.35
        rows.append(
            {
                "date": date,
                "open": round(open_price, 5),
                "high": round(high, 5),
                "low": round(low, 5),
                "close": round(close, 5),
                "volume": 0,
            }
        )

    return pd.DataFrame(rows)
