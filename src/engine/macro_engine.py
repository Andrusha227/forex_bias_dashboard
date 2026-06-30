"""Macro regime scoring for EUR/USD decision support."""

from __future__ import annotations

from typing import Any, Dict, List


ScoreResult = Dict[str, Any]


def score_macro_regime(data: Dict[str, Any]) -> ScoreResult:
    """Score macro regime as a capped filter for EUR/USD bias."""
    groups = data.get("groups", {})
    rates = score_rates(groups.get("rates", {}))
    inflation = score_inflation(groups.get("inflation", {}))
    labor = score_labor(groups.get("labor", {}))
    liquidity = score_liquidity(groups.get("liquidity", {}))
    growth = score_growth(groups.get("growth", {}))

    raw_score = (
        int(rates["score"])
        + int(inflation["score"])
        + int(labor["score"])
        + int(liquidity["score"])
        + int(growth["score"])
    )
    score = _cap(raw_score, -3, 3)

    if score >= 2:
        label = "Macro Tailwind"
    elif score <= -2:
        label = "Macro Headwind"
    else:
        label = "Macro Mixed"

    return {
        "score": score,
        "raw_score": raw_score,
        "label": label,
        "sections": {
            "rates": rates,
            "inflation": inflation,
            "labor": labor,
            "liquidity": liquidity,
            "growth": growth,
        },
    }


def score_rates(data: Dict[str, Any]) -> ScoreResult:
    """Score Fed/rates regime. Falling US rates are EUR/USD supportive."""
    contributions: List[Dict[str, Any]] = []
    raw_score = 0

    for label in ("US2Y", "US5Y", "US10Y", "US30Y", "SOFR"):
        point = data.get(label)
        if not point:
            continue
        direction = point.get("direction")
        if direction == "falling":
            raw_score += 1
            _add(contributions, label, 1, f"{label} is falling")
        elif direction == "rising":
            raw_score -= 1
            _add(contributions, label, -1, f"{label} is rising")

    for label in ("Fed Funds", "EFFR", "Fed Target Upper", "Fed Target Lower"):
        point = data.get(label)
        if not point:
            continue
        direction = point.get("direction")
        if direction == "falling":
            raw_score += 1
            _add(contributions, label, 1, f"{label} is falling")
        elif direction == "rising":
            raw_score -= 1
            _add(contributions, label, -1, f"{label} is rising")

    return {"score": _cap(raw_score, -2, 2), "raw_score": raw_score, "contributions": contributions}


def score_inflation(data: Dict[str, Any]) -> ScoreResult:
    """Score inflation. Cooling inflation is EUR/USD supportive via softer Fed risk."""
    contributions: List[Dict[str, Any]] = []
    raw_score = 0
    for label in ("CPI", "PCE", "Sticky CPI"):
        point = data.get(label)
        if not point:
            continue
        direction = point.get("direction")
        if direction == "falling":
            raw_score += 1
            _add(contributions, label, 1, f"{label} is cooling")
        elif direction == "rising":
            raw_score -= 1
            _add(contributions, label, -1, f"{label} is heating up")
    return {"score": _cap(raw_score, -1, 1), "raw_score": raw_score, "contributions": contributions}


def score_labor(data: Dict[str, Any]) -> ScoreResult:
    """Score labor. Weaker US labor is EUR/USD supportive via cut expectations."""
    contributions: List[Dict[str, Any]] = []
    raw_score = 0

    payrolls = data.get("Payrolls")
    if payrolls:
        if payrolls.get("direction") == "falling":
            raw_score += 1
            _add(contributions, "Payrolls", 1, "Payrolls are weakening")
        elif payrolls.get("direction") == "rising":
            raw_score -= 1
            _add(contributions, "Payrolls", -1, "Payrolls are strengthening")

    for label in ("Unemployment", "Initial Claims"):
        point = data.get(label)
        if not point:
            continue
        if point.get("direction") == "rising":
            raw_score += 1
            _add(contributions, label, 1, f"{label} is rising")
        elif point.get("direction") == "falling":
            raw_score -= 1
            _add(contributions, label, -1, f"{label} is falling")

    return {"score": _cap(raw_score, -1, 1), "raw_score": raw_score, "contributions": contributions}


def score_liquidity(data: Dict[str, Any]) -> ScoreResult:
    """Score liquidity and dollar backdrop."""
    contributions: List[Dict[str, Any]] = []
    raw_score = 0

    balance_sheet = data.get("Fed Balance Sheet")
    if balance_sheet:
        if balance_sheet.get("direction") == "rising":
            raw_score += 1
            _add(contributions, "Fed Balance Sheet", 1, "Fed balance sheet is expanding")
        elif balance_sheet.get("direction") == "falling":
            raw_score -= 1
            _add(contributions, "Fed Balance Sheet", -1, "Fed balance sheet is contracting")

    sofr = data.get("SOFR")
    if sofr:
        if sofr.get("direction") == "falling":
            raw_score += 1
            _add(contributions, "SOFR", 1, "SOFR is falling")
        elif sofr.get("direction") == "rising":
            raw_score -= 1
            _add(contributions, "SOFR", -1, "SOFR is rising")

    dollar = data.get("Trade Weighted Dollar")
    if dollar:
        if dollar.get("direction") == "falling":
            raw_score += 1
            _add(contributions, "Trade Weighted Dollar", 1, "Broad USD index is falling")
        elif dollar.get("direction") == "rising":
            raw_score -= 1
            _add(contributions, "Trade Weighted Dollar", -1, "Broad USD index is rising")

    return {"score": _cap(raw_score, -1, 1), "raw_score": raw_score, "contributions": contributions}


def score_growth(data: Dict[str, Any]) -> ScoreResult:
    """Score growth as a low-weight context block."""
    contributions: List[Dict[str, Any]] = []
    raw_score = 0

    for label in ("GDP", "Retail Sales", "Industrial Production"):
        point = data.get(label)
        if not point:
            continue
        direction = point.get("direction")
        if direction == "falling":
            raw_score += 1
            _add(contributions, label, 1, f"{label} is weakening")
        elif direction == "rising":
            raw_score -= 1
            _add(contributions, label, -1, f"{label} is strengthening")

    return {"score": _cap(raw_score, -1, 1), "raw_score": raw_score, "contributions": contributions}


def _add(contributions: List[Dict[str, Any]], name: str, value: int, reason: str) -> None:
    contributions.append({"name": name, "value": value, "reason": reason})


def _cap(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))
