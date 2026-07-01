"""Normalized scoring utilities for the EUR/USD bias dashboard.

Design
------
Each macro factor produces a directional signal in [-1.0, +1.0]:
  +1.0 = Bullish EUR/USD
  -1.0 = Bearish EUR/USD
   0.0 = Neutral
  None = Unavailable (excluded from scoring)

Signals are grouped into *categories*.  A category score is the
arithmetic mean of its available signals, producing a value in [-1, +1].

The final normalized score is the weighted average of available
category scores, again in [-1, +1].

Verdict thresholds (conservative — avoids directional bias when
conviction is weak):
  >= +0.70  Strong Bullish
  +0.50..+0.69  Bullish
  -0.49..+0.49  Neutral / Mixed
  -0.50..-0.69  Bearish
  <= -0.70  Strong Bearish
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FactorSignal:
    """One directional factor contributing to a category."""

    name: str
    signal: Optional[float]  # None = unavailable
    reason: str = ""
    timestamp: str = "n/a"
    source: str = "n/a"
    freshness: str = "unknown"


@dataclass
class CategoryResult:
    """Aggregated score for one scoring category."""

    name: str
    weight: float
    factors: List[FactorSignal] = field(default_factory=list)

    # Computed after construction
    score: Optional[float] = None      # None when all factors unavailable
    available_count: int = 0
    total_count: int = 0
    status: str = "ok"                  # "ok", "partial", "unavailable"

    def compute(self) -> None:
        """Derive score and availability from the factor list."""
        self.total_count = len(self.factors)
        available = [f for f in self.factors if f.signal is not None]
        self.available_count = len(available)

        if not available:
            self.score = None
            self.status = "unavailable"
        else:
            self.score = sum(f.signal for f in available) / len(available)
            self.status = "ok" if self.available_count == self.total_count else "partial"


def normalize_score(categories: List[CategoryResult]) -> Optional[float]:
    """Return the weighted average of available category scores in [-1, +1].

    Returns ``None`` when no category has data.
    """
    numerator = 0.0
    denominator = 0.0
    for cat in categories:
        if cat.score is not None:
            numerator += cat.score * cat.weight
            denominator += cat.weight
    if denominator == 0.0:
        return None
    return numerator / denominator


def classify_verdict(normalized: Optional[float]) -> str:
    """Map a normalized score to one of five verdict tiers."""
    if normalized is None:
        return "Insufficient Data"
    if normalized >= 0.70:
        return "Strong Bullish EUR/USD"
    if normalized >= 0.50:
        return "Bullish EUR/USD"
    if normalized <= -0.70:
        return "Strong Bearish EUR/USD"
    if normalized <= -0.50:
        return "Bearish EUR/USD"
    return "Neutral / Mixed"


def build_scoring_summary(
    categories: List[CategoryResult],
) -> Dict[str, Any]:
    """Build a structured dict for the UI layer."""
    normalized = normalize_score(categories)
    verdict = classify_verdict(normalized)

    available_weight = sum(c.weight for c in categories if c.score is not None)
    total_weight = sum(c.weight for c in categories)

    cat_details = []
    for cat in categories:
        renormalized_weight = (cat.weight / available_weight) if (cat.score is not None and available_weight > 0.0) else 0.0
        normalized_contribution = cat.score * renormalized_weight if cat.score is not None else 0.0

        factors_list = []
        for f in cat.factors:
            factors_list.append({
                "name": f.name,
                "signal": f.signal,
                "reason": f.reason,
                "timestamp": f.timestamp,
                "source": f.source,
                "freshness": f.freshness,
            })
        cat_details.append({
            "name": cat.name,
            "weight": cat.weight,
            "renormalized_weight": renormalized_weight,
            "normalized_contribution": normalized_contribution,
            "score": cat.score,
            "status": cat.status,
            "available_count": cat.available_count,
            "total_count": cat.total_count,
            "factors": factors_list,
        })

    return {
        "normalized_score": normalized,
        "verdict": verdict,
        "available_weight": available_weight,
        "total_weight": total_weight,
        "partial": available_weight < total_weight,
        "categories": cat_details,
    }
