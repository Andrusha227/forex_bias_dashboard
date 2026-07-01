"""FRED series catalog used by the macro regime layer.

Weighting rationale — duplicate / correlation avoidance:
  • DFF kept as the sole Fed-policy-rate series.
    EFFR, DFEDTARU, DFEDTARL removed: they move in lock-step with DFF
    and would over-weight a single policy decision.
  • DGS3MO, DGS1 removed: dominated by the policy rate already
    captured by DFF; adds noise without new information.
  • DTWEXBGS (Trade-Weighted Broad Dollar) removed: highly correlated
    with DXY which is already scored in the Weekly Structure category.
  • WTREGEN (Treasury General Account) and RRPONTSYD (Overnight Reverse
    Repo) added to enable the Net Liquidity indicator:
    Net Liquidity = WALCL − WTREGEN − RRPONTSYD
"""

from __future__ import annotations

from typing import Dict


FRED_SERIES: Dict[str, Dict[str, str]] = {
    "rates": {
        "Fed Funds": "DFF",
        "US2Y": "DGS2",
        "US5Y": "DGS5",
        "US10Y": "DGS10",
        "US30Y": "DGS30",
    },
    "inflation": {
        "CPI": "CPIAUCSL",
        "PCE": "PCEPI",
        "Sticky CPI": "CORESTICKM159SFRBATL",
    },
    "labor": {
        "Payrolls": "PAYEMS",
        "Unemployment": "UNRATE",
        "Initial Claims": "ICSA",
    },
    "liquidity": {
        "Fed Balance Sheet": "WALCL",
        "Treasury General Account": "WTREGEN",
        "Reverse Repo": "RRPONTSYD",
        "SOFR": "SOFR",
    },
    "growth": {
        "GDP": "GDP",
        "Retail Sales": "RSAFS",
        "Industrial Production": "INDPRO",
    },
}
