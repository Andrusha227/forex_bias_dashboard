"""Normalized scoring engine for EUR/USD macro bias.

Category weights:
  Monthly Structure: 3 — highest-timeframe price structure
  Weekly Structure:  2 — active trading-week context
  Rates & Yield Curve: 2 — primary FX driver
  Liquidity: 2 — risk appetite driver
  Inflation: 1.5 — rate expectations context
  Labor: 1.5 — Fed policy context
  Growth: 1 — backdrop context
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engine.scoring import (
    CategoryResult,
    FactorSignal,
    build_scoring_summary,
    classify_verdict,
    normalize_score,
)


def score_monthly(data: Dict[str, Any]) -> CategoryResult:
    """Score monthly bias from price location and COT positioning."""
    cat = CategoryResult(name="Monthly Structure", weight=3)

    current_price = data.get("current_price")
    monthly_open_ranges = data.get("monthly_open_ranges")
    candles = data.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = data.get("history")

    eurusd_meta = data.get("eurusd_metadata") or {}
    cot_meta = data.get("cot_metadata") or {}

    # 1. Monthly Opening Range score (already in [-1, +1] from opening_engine)
    range_signal: Optional[float] = None
    range_reason = ""
    if current_price is not None and monthly_open_ranges:
        from src.engine.opening_engine import analyze_monthly_opening_range
        analysis = analyze_monthly_opening_range(float(current_price), monthly_open_ranges, candles)
        score_val = analysis.get("score", 0.0)
        state = analysis.get("state", "")
        # If score=0 and state='unknown', treat as unavailable
        if score_val == 0 and state == "unknown":
            range_signal = None
            range_reason = "Monthly range unavailable"
        else:
            range_signal = float(score_val)
            range_reason = analysis.get("score_reason", "")
    cat.factors.append(FactorSignal(
        name="Monthly Opening Range",
        signal=range_signal,
        reason=range_reason,
        timestamp=eurusd_meta.get("timestamp", "n/a"),
        source=eurusd_meta.get("source", "n/a"),
        freshness=eurusd_meta.get("freshness", "unknown"),
    ))

    # 2. COT Net Position
    cot_net = data.get("cot_net_position")
    cot_signal: Optional[float] = None
    cot_reason = ""
    if cot_net is not None:
        if cot_net > 0:
            cot_signal = 1.0
            cot_reason = "EUR net position is positive"
        elif cot_net < 0:
            cot_signal = -1.0
            cot_reason = "EUR net position is negative"
        else:
            cot_signal = 0.0
            cot_reason = "EUR net position is flat"
    cat.factors.append(FactorSignal(
        name="COT Net Position",
        signal=cot_signal,
        reason=cot_reason,
        timestamp=cot_meta.get("timestamp", "n/a"),
        source=cot_meta.get("source", "n/a"),
        freshness=cot_meta.get("freshness", "unknown"),
    ))

    # 3. COT Weekly Change
    cot_change = data.get("cot_weekly_change")
    change_signal: Optional[float] = None
    change_reason = ""
    if cot_change is not None:
        if cot_change > 0:
            change_signal = 1.0
            change_reason = "EUR net position increased week over week"
        elif cot_change < 0:
            change_signal = -1.0
            change_reason = "EUR net position decreased week over week"
        else:
            change_signal = 0.0
            change_reason = "EUR net position unchanged week over week"
    cat.factors.append(FactorSignal(
        name="COT Weekly Change",
        signal=change_signal,
        reason=change_reason,
        timestamp=cot_meta.get("timestamp", "n/a"),
        source=cot_meta.get("source", "n/a"),
        freshness=cot_meta.get("freshness", "unknown"),
    ))

    cat.compute()
    return cat


def score_weekly(data: Dict[str, Any]) -> CategoryResult:
    """Score weekly bias from EUR/USD opening range and DXY direction."""
    cat = CategoryResult(name="Weekly Structure", weight=2)

    current_price = data.get("current_price")
    weekly_open_ranges = data.get("weekly_open_ranges")
    candles = data.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = data.get("history")

    eurusd_meta = data.get("eurusd_metadata") or {}
    dxy_meta = data.get("dxy_metadata") or {}

    # 1. Weekly Opening Range score (already in [-1, +1] from opening_engine)
    range_signal: Optional[float] = None
    range_reason = ""
    if current_price is not None and weekly_open_ranges:
        from src.engine.opening_engine import analyze_weekly_opening_range
        analysis = analyze_weekly_opening_range(float(current_price), weekly_open_ranges, candles)
        score_val = analysis.get("score", 0.0)
        state = analysis.get("state", "")
        if score_val == 0 and state == "unknown":
            range_signal = None
            range_reason = "Weekly range unavailable"
        else:
            range_signal = float(score_val)
            range_reason = analysis.get("score_reason", "")
    cat.factors.append(FactorSignal(
        name="Weekly Opening Range",
        signal=range_signal,
        reason=range_reason,
        timestamp=eurusd_meta.get("timestamp", "n/a"),
        source=eurusd_meta.get("source", "n/a"),
        freshness=eurusd_meta.get("freshness", "unknown"),
    ))

    # 2. DXY Direction — falling = EUR+, rising = EUR-
    dxy_direction = str(data.get("dxy_direction", "")).lower()
    dxy_signal: Optional[float] = None
    dxy_reason = ""
    if dxy_direction == "falling":
        dxy_signal = 1.0
        dxy_reason = "DXY is falling"
    elif dxy_direction == "rising":
        dxy_signal = -1.0
        dxy_reason = "DXY is rising"
    cat.factors.append(FactorSignal(
        name="DXY Direction",
        signal=dxy_signal,
        reason=dxy_reason,
        timestamp=dxy_meta.get("timestamp", "n/a"),
        source=dxy_meta.get("source", "n/a"),
        freshness=dxy_meta.get("freshness", "unknown"),
    ))

    cat.compute()
    return cat


def score_total(categories: List[CategoryResult]) -> Dict[str, Any]:
    """Combine all category results into a final normalized score and verdict.

    Returns a dict with:
      - 'normalized_score': float in [-1, +1] or None
      - 'verdict': one of 5 verdict tiers
      - 'categories': list of per-category detail dicts
      - 'partial': bool — whether any data was missing
    """
    return build_scoring_summary(categories)
