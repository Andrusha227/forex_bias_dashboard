"""FRED series catalog used by the macro regime layer."""

from __future__ import annotations

from typing import Dict


FRED_SERIES: Dict[str, Dict[str, str]] = {
    "rates": {
        "Fed Funds": "DFF",
        "EFFR": "EFFR",
        "Fed Target Upper": "DFEDTARU",
        "Fed Target Lower": "DFEDTARL",
        "US3M": "DGS3MO",
        "US1Y": "DGS1",
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
        "SOFR": "SOFR",
        "Trade Weighted Dollar": "DTWEXBGS",
    },
    "growth": {
        "GDP": "GDP",
        "Retail Sales": "RSAFS",
        "Industrial Production": "INDPRO",
    },
}

