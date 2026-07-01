"""Macro regime scoring for EUR/USD decision support.

Weighting rationale:
  Rates & Yield Curve (weight 2) — primary FX driver
  Inflation (weight 1.5) — influences rate expectations
  Labor (weight 1.5) — influences Fed policy path
  Liquidity (weight 2) — directly affects risk appetite
  Growth (weight 1) — backdrop context, less actionable
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from src.engine.scoring import CategoryResult, FactorSignal


def _direction_signal(
    point: Optional[Dict[str, Any]],
    invert: bool = False,
) -> Optional[int]:
    """Return +1, -1, 0, or None based on a data point's direction field.

    Normal:   falling → +1  (EUR-positive), rising → -1
    Inverted: rising  → +1, falling → -1  (for metrics where *rising* is EUR+)
    """
    if point is None:
        return None
    direction = point.get("direction")
    if direction == "falling":
        return -1 if invert else 1
    if direction == "rising":
        return 1 if invert else -1
    return 0


# -------------------------------------------------------------------
# Category scorers
# -------------------------------------------------------------------

def score_rates(data: Dict[str, Any]) -> CategoryResult:
    """Score Fed/rates regime.  Falling US rates are EUR/USD supportive."""
    cat = CategoryResult(name="Rates & Yield Curve", weight=2)

    # 1. Fed Policy (DFF)
    fed = data.get("Fed Funds")
    sig = _direction_signal(fed)
    reason = ""
    if sig == 1:
        reason = "Fed Funds rate is falling"
    elif sig == -1:
        reason = "Fed Funds rate is rising"
    cat.factors.append(FactorSignal(
        name="Fed Policy",
        signal=sig,
        reason=reason,
        timestamp=fed.get("timestamp", "n/a") if fed else "n/a",
        source=fed.get("source", "n/a") if fed else "n/a",
        freshness=fed.get("freshness", "unknown") if fed else "unknown",
    ))

    # 2. Yield Curve Direction — average of available treasury yields
    yield_labels = ("US2Y", "US5Y", "US10Y", "US30Y")
    signals: List[int] = []
    parts: List[str] = []
    meta_point = None
    for label in yield_labels:
        pt = data.get(label)
        s = _direction_signal(pt)
        if s is not None:
            signals.append(s)
            parts.append(label)
            if meta_point is None:
                meta_point = pt
    if signals:
        avg = sum(signals) / len(signals)
        reason = f"Avg direction of {', '.join(parts)}"
        cat.factors.append(FactorSignal(
            name="Yield Curve Direction",
            signal=avg,
            reason=reason,
            timestamp=meta_point.get("timestamp", "n/a") if meta_point else "n/a",
            source=meta_point.get("source", "n/a") if meta_point else "n/a",
            freshness=meta_point.get("freshness", "unknown") if meta_point else "unknown",
        ))
    else:
        cat.factors.append(FactorSignal(name="Yield Curve Direction", signal=None, reason="No yield data"))

    # 3. Yield Spread Direction (passed in externally)
    spread = data.get("yield_spread")
    if spread is not None:
        spread_dir = spread.get("direction") if isinstance(spread, dict) else None
        if spread_dir == "steepening":
            cat.factors.append(FactorSignal(
                name="Yield Spread Direction",
                signal=1.0,
                reason="Yield spread is steepening (10Y−2Y widening)",
                timestamp=spread.get("timestamp", "n/a") if isinstance(spread, dict) else "n/a",
                source=spread.get("source", "n/a") if isinstance(spread, dict) else "n/a",
                freshness=spread.get("freshness", "unknown") if isinstance(spread, dict) else "unknown",
            ))
        elif spread_dir == "flattening":
            cat.factors.append(FactorSignal(
                name="Yield Spread Direction",
                signal=-1.0,
                reason="Yield spread is flattening (10Y−2Y narrowing)",
                timestamp=spread.get("timestamp", "n/a") if isinstance(spread, dict) else "n/a",
                source=spread.get("source", "n/a") if isinstance(spread, dict) else "n/a",
                freshness=spread.get("freshness", "unknown") if isinstance(spread, dict) else "unknown",
            ))
        else:
            cat.factors.append(FactorSignal(name="Yield Spread Direction", signal=None, reason="Spread direction unclear"))
    else:
        cat.factors.append(FactorSignal(name="Yield Spread Direction", signal=None, reason="No spread data"))

    cat.compute()
    return cat


def score_inflation(data: Dict[str, Any]) -> CategoryResult:
    """Score inflation.  Cooling inflation is EUR/USD supportive via softer Fed risk."""
    cat = CategoryResult(name="Inflation", weight=1.5)

    for label in ("CPI", "PCE", "Sticky CPI"):
        point = data.get(label)
        sig = _direction_signal(point)
        reason = ""
        if sig == 1:
            reason = f"{label} is cooling"
        elif sig == -1:
            reason = f"{label} is heating up"
        cat.factors.append(FactorSignal(
            name=label,
            signal=sig,
            reason=reason,
            timestamp=point.get("timestamp", "n/a") if point else "n/a",
            source=point.get("source", "n/a") if point else "n/a",
            freshness=point.get("freshness", "unknown") if point else "unknown",
        ))

    cat.compute()
    return cat


def score_labor(data: Dict[str, Any]) -> CategoryResult:
    """Score labor.  Weaker US labor is EUR/USD supportive via cut expectations."""
    cat = CategoryResult(name="Labor", weight=1.5)

    # Payrolls — normal direction (falling = weaker = EUR+)
    payrolls = data.get("Payrolls")
    sig = _direction_signal(payrolls)
    reason = ""
    if sig == 1:
        reason = "Payrolls are weakening"
    elif sig == -1:
        reason = "Payrolls are strengthening"
    cat.factors.append(FactorSignal(
        name="Payrolls",
        signal=sig,
        reason=reason,
        timestamp=payrolls.get("timestamp", "n/a") if payrolls else "n/a",
        source=payrolls.get("source", "n/a") if payrolls else "n/a",
        freshness=payrolls.get("freshness", "unknown") if payrolls else "unknown",
    ))

    # Unemployment — INVERTED (rising = weaker labor = EUR+)
    unemployment = data.get("Unemployment")
    sig = _direction_signal(unemployment, invert=True)
    reason = ""
    if sig == 1:
        reason = "Unemployment is rising"
    elif sig == -1:
        reason = "Unemployment is falling"
    cat.factors.append(FactorSignal(
        name="Unemployment",
        signal=sig,
        reason=reason,
        timestamp=unemployment.get("timestamp", "n/a") if unemployment else "n/a",
        source=unemployment.get("source", "n/a") if unemployment else "n/a",
        freshness=unemployment.get("freshness", "unknown") if unemployment else "unknown",
    ))

    # Initial Claims — INVERTED (rising = weaker labor = EUR+)
    claims = data.get("Initial Claims")
    sig = _direction_signal(claims, invert=True)
    reason = ""
    if sig == 1:
        reason = "Initial Claims are rising"
    elif sig == -1:
        reason = "Initial Claims are falling"
    cat.factors.append(FactorSignal(
        name="Initial Claims",
        signal=sig,
        reason=reason,
        timestamp=claims.get("timestamp", "n/a") if claims else "n/a",
        source=claims.get("source", "n/a") if claims else "n/a",
        freshness=claims.get("freshness", "unknown") if claims else "unknown",
    ))

    cat.compute()
    return cat


def score_liquidity(
    data: Dict[str, Any],
    net_liquidity: Optional[Dict[str, Any]] = None,
) -> CategoryResult:
    """Score liquidity.  Rising net liquidity / falling SOFR are EUR/USD supportive."""
    cat = CategoryResult(name="Liquidity", weight=2)

    # Net Liquidity — passed in as a dict with 'direction' key
    if net_liquidity is not None:
        sig = _direction_signal(net_liquidity, invert=True)  # rising = +1
        reason = ""
        if sig == 1:
            reason = "Net liquidity is rising (risk-on)"
        elif sig == -1:
            reason = "Net liquidity is falling (risk-off)"
        cat.factors.append(FactorSignal(
            name="Net Liquidity",
            signal=sig,
            reason=reason,
            timestamp=net_liquidity.get("timestamp", "n/a"),
            source=net_liquidity.get("source", "n/a"),
            freshness=net_liquidity.get("freshness", "unknown"),
        ))
    else:
        cat.factors.append(FactorSignal(name="Net Liquidity", signal=None, reason="No net liquidity data"))

    # SOFR — falling = easier funding = EUR+
    sofr = data.get("SOFR")
    sig = _direction_signal(sofr)
    reason = ""
    if sig == 1:
        reason = "SOFR is falling (easier funding)"
    elif sig == -1:
        reason = "SOFR is rising (tighter funding)"
    cat.factors.append(FactorSignal(
        name="SOFR",
        signal=sig,
        reason=reason,
        timestamp=sofr.get("timestamp", "n/a") if sofr else "n/a",
        source=sofr.get("source", "n/a") if sofr else "n/a",
        freshness=sofr.get("freshness", "unknown") if sofr else "unknown",
    ))

    cat.compute()
    return cat


def score_growth(data: Dict[str, Any]) -> CategoryResult:
    """Score growth as a low-weight context block.  Weaker growth → more likely Fed easing → EUR+."""
    cat = CategoryResult(name="Growth", weight=1)

    for label in ("GDP", "Retail Sales", "Industrial Production"):
        point = data.get(label)
        sig = _direction_signal(point)
        reason = ""
        if sig == 1:
            reason = f"{label} is weakening"
        elif sig == -1:
            reason = f"{label} is strengthening"
        cat.factors.append(FactorSignal(
            name=label,
            signal=sig,
            reason=reason,
            timestamp=point.get("timestamp", "n/a") if point else "n/a",
            source=point.get("source", "n/a") if point else "n/a",
            freshness=point.get("freshness", "unknown") if point else "unknown",
        ))

    cat.compute()
    return cat


# -------------------------------------------------------------------
# Top-level macro regime scorer
# -------------------------------------------------------------------

def score_macro_regime(
    macro_data: Dict[str, Any],
    yield_spread: Optional[Dict[str, Any]] = None,
    net_liquidity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute macro regime from grouped macro indicators.

    Returns a dict with:
      - 'categories': list of CategoryResult objects
      - 'label':  'Macro Tailwind' / 'Macro Headwind' / 'Macro Mixed'
    """
    groups = macro_data.get("groups", {})

    rates_data = groups.get("rates", {})
    if yield_spread is not None:
        rates_data = {**rates_data, "yield_spread": yield_spread}

    categories: List[CategoryResult] = [
        score_rates(rates_data),
        score_inflation(groups.get("inflation", {})),
        score_labor(groups.get("labor", {})),
        score_liquidity(groups.get("liquidity", {}), net_liquidity=net_liquidity),
        score_growth(groups.get("growth", {})),
    ]

    # Compute a combined normalized macro score for the regime label
    from src.engine.scoring import normalize_score
    norm = normalize_score(categories)

    if norm is not None and norm >= 0.30:
        label = "Macro Tailwind"
    elif norm is not None and norm <= -0.30:
        label = "Macro Headwind"
    else:
        label = "Macro Mixed"

    return {
        "categories": categories,
        "label": label,
    }
