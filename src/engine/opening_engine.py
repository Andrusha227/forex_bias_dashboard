"""Opening range analysis for display-only trade filters."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def analyze_opening_range(
    current_price: float,
    opening_range: Optional[Dict[str, Any]],
    candles: Optional[pd.DataFrame],
) -> Dict[str, Any]:
    """Analyze current location and wick raids around an opening range."""
    if not opening_range:
        return {
            "state": "unknown",
            "css_class": "open-flat",
            "text_class": "",
            "label": "Opening range unavailable",
            "detail": "No candle source available.",
            "raid_high": False,
            "raid_low": False,
        }

    high = max(float(opening_range["high"]), float(opening_range["low"]))
    low = min(float(opening_range["high"]), float(opening_range["low"]))
    opened_at = opening_range.get("time_utc")
    after = _candles_after(candles, opened_at)
    raid_high = bool(after is not None and not after.empty and float(after["high"].max()) > high)
    raid_low = bool(after is not None and not after.empty and float(after["low"].min()) < low)

    if low <= current_price <= high:
        state = "inside"
        css_class = "open-flat"
        text_class = ""
        label = "Inside range"
    elif current_price > high:
        state = "above"
        css_class = "open-above"
        text_class = "opening-struck" if raid_low else ""
        label = "Above range"
    else:
        state = "below"
        css_class = "open-below"
        text_class = "opening-struck" if raid_high else ""
        label = "Below range"

    detail_bits = []
    if raid_high:
        detail_bits.append("raid high")
    if raid_low:
        detail_bits.append("raid low")
    detail = ", ".join(detail_bits) if detail_bits else "no raid yet"

    return {
        "state": state,
        "css_class": css_class,
        "text_class": text_class,
        "label": label,
        "detail": detail,
        "raid_high": raid_high,
        "raid_low": raid_low,
        "open": float(opening_range["open"]),
        "high": high,
        "low": low,
        "source_label": opening_range.get("label", ""),
    }


def _candles_after(candles: Optional[pd.DataFrame], opened_at: Any) -> Optional[pd.DataFrame]:
    if candles is None or candles.empty or opened_at is None:
        return None
    return candles[candles["date"] > pd.Timestamp(opened_at)]


def analyze_monthly_opening_range(
    current_price: float,
    monthly_ranges: Optional[Dict[str, Any]],
    candles: Optional[pd.DataFrame],
) -> Dict[str, Any]:
    """Analyze monthly open range using the dynamic D/W transition and custom float scoring.

    Rules:
    - If after first week and D was swept during the first week, we use the W candle range.
    - Otherwise, we use the D candle range.
    - Scoring:
      - Below active range + raid high: -1.0
      - Below active range + no raid high: +0.5
      - Above active range + raid low: +1.0
      - Above active range + no raid low: -0.5
      - Inside active range: 0.0
    """
    if not monthly_ranges:
        return {
            "state": "unknown",
            "css_class": "open-flat",
            "text_class": "",
            "label": "Monthly range unavailable",
            "detail": "No monthly context.",
            "raid_high": False,
            "raid_low": False,
            "score": 0.0,
            "score_reason": "No range context available",
            "active_source": "D"
        }

    active_source = monthly_ranges.get("active_source", "D")
    range_key = "w_open" if active_source == "W" else "d_open"
    opening_range = monthly_ranges.get(range_key)

    if not opening_range:
        return {
            "state": "unknown",
            "css_class": "open-flat",
            "text_class": "",
            "label": "Monthly open range unavailable",
            "detail": f"Monthly {active_source} range unavailable.",
            "raid_high": False,
            "raid_low": False,
            "score": 0.0,
            "score_reason": "Range data missing",
            "active_source": active_source
        }

    high = max(float(opening_range["high"]), float(opening_range["low"]))
    low = min(float(opening_range["high"]), float(opening_range["low"]))
    opened_at = opening_range.get("time_utc")

    # Check raids of the active range since it opened
    after = _candles_after(candles, opened_at)
    raid_high = bool(after is not None and not after.empty and float(after["high"].max()) > high)
    raid_low = bool(after is not None and not after.empty and float(after["low"].min()) < low)

    # Custom scoring and states
    if low <= current_price <= high:
        state = "inside"
        css_class = "open-flat"
        text_class = ""
        label = "Inside range"
        score = 0.0
        score_reason = f"Price is inside the active Monthly Open {active_source} range"
    elif current_price > high:
        state = "above"
        css_class = "open-above"
        if raid_low:
            text_class = "opening-struck"
            score = 1.0
            score_reason = f"Price is above Monthly Open {active_source} range with low raid (+1.0)"
        else:
            text_class = ""
            score = -0.5
            score_reason = f"Price is above Monthly Open {active_source} range (clean open target, -0.5)"
        label = "Above range"
    else:
        state = "below"
        css_class = "open-below"
        if raid_high:
            text_class = "opening-struck"
            score = -1.0
            score_reason = f"Price is below Monthly Open {active_source} range with high raid (-1.0)"
        else:
            text_class = ""
            score = 0.5
            score_reason = f"Price is below Monthly Open {active_source} range (clean open target, +0.5)"
        label = "Below range"

    detail_bits = []
    if raid_high:
        detail_bits.append("raid high")
    if raid_low:
        detail_bits.append("raid low")
    detail = ", ".join(detail_bits) if detail_bits else "no raid yet"

    return {
        "state": state,
        "css_class": css_class,
        "text_class": text_class,
        "label": label,
        "detail": detail,
        "raid_high": raid_high,
        "raid_low": raid_low,
        "open": float(opening_range["open"]),
        "high": high,
        "low": low,
        "source_label": opening_range.get("label", ""),
        "active_source": active_source,
        "score": score,
        "score_reason": score_reason
    }


def analyze_weekly_opening_range(
    current_price: float,
    weekly_ranges: Optional[Dict[str, Any]],
    candles: Optional[pd.DataFrame],
) -> Dict[str, Any]:
    """Analyze weekly open range using the dynamic transition and custom float scoring.

    Rules:
    - If after Monday and Monday's 4H range was NOT swept on Monday, we use the Monday Daily range.
    - Otherwise, we use the Monday 4H range.
    - Scoring:
      - Below active range + raid high: -1.0
      - Below active range + no raid high: +0.5
      - Above active range + raid low: +1.0
      - Above active range + no raid low: -0.5
      - Inside active range: 0.0
    """
    if not weekly_ranges:
        return {
            "state": "unknown",
            "css_class": "open-flat",
            "text_class": "",
            "label": "Weekly range unavailable",
            "detail": "No weekly context.",
            "raid_high": False,
            "raid_low": False,
            "score": 0.0,
            "score_reason": "No range context available",
            "active_source": "4H"
        }

    active_source = weekly_ranges.get("active_source", "4H")
    range_key = "monday_d" if active_source == "D" else "monday_open"
    opening_range = weekly_ranges.get(range_key)

    if not opening_range:
        opening_range = weekly_ranges.get("sunday_open")
        active_source = "Sunday"

    if not opening_range:
        return {
            "state": "unknown",
            "css_class": "open-flat",
            "text_class": "",
            "label": "Weekly open range unavailable",
            "detail": f"Weekly {active_source} range unavailable.",
            "raid_high": False,
            "raid_low": False,
            "score": 0.0,
            "score_reason": "Range data missing",
            "active_source": active_source
        }

    high = max(float(opening_range["high"]), float(opening_range["low"]))
    low = min(float(opening_range["high"]), float(opening_range["low"]))
    opened_at = opening_range.get("time_utc")

    # Check raids of the active range since it opened
    after = _candles_after(candles, opened_at)
    raid_high = bool(after is not None and not after.empty and float(after["high"].max()) > high)
    raid_low = bool(after is not None and not after.empty and float(after["low"].min()) < low)

    # Custom scoring and states (same as monthly)
    if low <= current_price <= high:
        state = "inside"
        css_class = "open-flat"
        text_class = ""
        label = "Inside range"
        score = 0.0
        score_reason = f"Price is inside the active Weekly Open {active_source} range"
    elif current_price > high:
        state = "above"
        css_class = "open-above"
        if raid_low:
            text_class = "opening-struck"
            score = 1.0
            score_reason = f"Price is above Weekly Open {active_source} range with low raid (+1.0)"
        else:
            text_class = ""
            score = -0.5
            score_reason = f"Price is above Weekly Open {active_source} range (clean open target, -0.5)"
        label = "Above range"
    else:
        state = "below"
        css_class = "open-below"
        if raid_high:
            text_class = "opening-struck"
            score = -1.0
            score_reason = f"Price is below Weekly Open {active_source} range with high raid (-1.0)"
        else:
            text_class = ""
            score = 0.5
            score_reason = f"Price is below Weekly Open {active_source} range (clean open target, +0.5)"
        label = "Below range"

    detail_bits = []
    if raid_high:
        detail_bits.append("raid high")
    if raid_low:
        detail_bits.append("raid low")
    detail = ", ".join(detail_bits) if detail_bits else "no raid yet"

    return {
        "state": state,
        "css_class": css_class,
        "text_class": text_class,
        "label": label,
        "detail": detail,
        "raid_high": raid_high,
        "raid_low": raid_low,
        "open": float(opening_range["open"]),
        "high": high,
        "low": low,
        "source_label": opening_range.get("label", ""),
        "active_source": active_source,
        "score": score,
        "score_reason": score_reason
    }
