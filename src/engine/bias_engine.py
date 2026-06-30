"""Pure scoring functions for EUR/USD macro bias."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


ScoreResult = Dict[str, Any]


def _add_contribution(
    contributions: List[Dict[str, Any]],
    name: str,
    value: int,
    reason: str,
) -> None:
    contributions.append({"name": name, "value": value, "reason": reason})


def score_monthly(data: Dict[str, Any]) -> ScoreResult:
    """Score monthly bias from price location and COT positioning."""
    score = 0
    contributions: List[Dict[str, Any]] = []

    current_price = data.get("current_price")
    monthly_open_ranges = data.get("monthly_open_ranges")
    candles = data.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = data.get("history")

    cot_net = data.get("cot_net_position")
    cot_change = data.get("cot_weekly_change")

    if current_price is not None and monthly_open_ranges:
        from src.engine.opening_engine import analyze_monthly_opening_range
        analysis = analyze_monthly_opening_range(float(current_price), monthly_open_ranges, candles)
        range_score = analysis.get("score", 0.0)
        score += range_score
        _add_contribution(
            contributions,
            f"Monthly open range ({analysis.get('active_source', 'D')})",
            range_score,
            analysis.get("score_reason", "")
        )

    if cot_net is not None:
        if cot_net > 0:
            score += 1
            _add_contribution(contributions, "COT net", 1, "EUR net position is positive")
        elif cot_net < 0:
            score -= 1
            _add_contribution(contributions, "COT net", -1, "EUR net position is negative")

    if cot_change is not None:
        if cot_change > 0:
            score += 1
            _add_contribution(contributions, "COT weekly change", 1, "EUR net position increased week over week")
        elif cot_change < 0:
            score -= 1
            _add_contribution(contributions, "COT weekly change", -1, "EUR net position decreased week over week")

    return {"score": score, "contributions": contributions}


def score_weekly(data: Dict[str, Any]) -> ScoreResult:
    """Score weekly bias from EUR/USD, DXY, and US yield direction."""
    score = 0
    contributions: List[Dict[str, Any]] = []

    current_price = data.get("current_price")
    weekly_open_ranges = data.get("weekly_open_ranges")
    candles = data.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = data.get("history")

    if current_price is not None and weekly_open_ranges:
        from src.engine.opening_engine import analyze_weekly_opening_range
        analysis = analyze_weekly_opening_range(float(current_price), weekly_open_ranges, candles)
        range_score = analysis.get("score", 0.0)
        score += range_score
        _add_contribution(
            contributions,
            f"Weekly open range ({analysis.get('active_source', '4H')})",
            range_score,
            analysis.get("score_reason", "")
        )

    direction_rules = {
        "dxy_direction": ("DXY", "falling", "rising"),
        "us2y_direction": ("US2Y", "falling", "rising"),
        "us10y_direction": ("US10Y", "falling", "rising"),
    }

    for key, (label, bullish_value, bearish_value) in direction_rules.items():
        direction = str(data.get(key, "")).lower()
        if direction == bullish_value:
            score += 1
            _add_contribution(contributions, label, 1, f"{label} is falling")
        elif direction == bearish_value:
            score -= 1
            _add_contribution(contributions, label, -1, f"{label} is rising")

    return {"score": score, "contributions": contributions}


def score_intraday(data: Dict[str, Any]) -> ScoreResult:
    """Score intraday context from Asia range and news risk."""
    score = 0
    contributions: List[Dict[str, Any]] = []

    current_price = data.get("current_price")
    asia_high = data.get("asia_high")
    asia_low = data.get("asia_low")
    news_within_60m = bool(data.get("news_within_60m"))

    if current_price is not None and asia_high is not None and current_price > asia_high:
        score += 1
        _add_contribution(contributions, "Asia high", 1, "Price reclaimed Asia high")
    elif current_price is not None and asia_low is not None and current_price < asia_low:
        score -= 1
        _add_contribution(contributions, "Asia low", -1, "Price broke Asia low")

    if news_within_60m:
        score -= 1
        _add_contribution(contributions, "High impact news", -1, "High impact news is within the next 60 minutes")

    return {"score": score, "contributions": contributions}


def score_total(
    monthly: ScoreResult,
    weekly: ScoreResult,
    intraday: ScoreResult,
    macro: Optional[ScoreResult] = None,
) -> ScoreResult:
    """Combine section scores and return the final label."""
    core_score = int(monthly.get("score", 0)) + int(weekly.get("score", 0)) + int(intraday.get("score", 0))
    macro_score = int((macro or {}).get("score", 0))
    total = core_score + macro_score

    if total >= 3:
        label = "Bullish EUR/USD"
    elif total <= -3:
        label = "Bearish EUR/USD"
    else:
        label = "Neutral / Wait"

    return {"score": total, "core_score": core_score, "macro_score": macro_score, "label": label}
