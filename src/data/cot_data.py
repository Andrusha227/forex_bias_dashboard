"""CFTC COT adapter for Euro FX with mock fallback."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import requests


CFTC_CURRENT_LEGACY_URL = "https://www.cftc.gov/dea/newcot/deafut.txt"


def get_euro_fx_cot() -> Dict[str, Any]:
    """Return Euro FX non-commercial net position and weekly change.

    The parser targets the public CFTC legacy text report. If the format changes
    or the network is unavailable, deterministic mock data is returned.
    """
    try:
        response = requests.get(
            CFTC_CURRENT_LEGACY_URL,
            timeout=10,
            headers={"User-Agent": "eurusd-bias-dashboard/0.1"},
        )
        response.raise_for_status()
        parsed = _parse_legacy_report(response.text)
        if parsed is None:
            raise ValueError("Euro FX COT row was not found")
        return parsed
    except Exception:
        return _mock_cot()


def _parse_legacy_report(text: str) -> Optional[Dict[str, Any]]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "EURO FX" not in line.upper():
            continue

        window = "\n".join(lines[index : index + 8])
        numbers = [int(token.replace(",", "")) for token in window.replace("-", " -").split() if _is_int(token)]
        if len(numbers) < 8:
            continue

        # Legacy report rows expose non-commercial long/short values near the
        # start of the market block. This is intentionally conservative.
        non_commercial_long = numbers[0]
        non_commercial_short = numbers[1]
        net_position = non_commercial_long - non_commercial_short

        # Weekly change is not stable across every public text layout, so use a
        # neutral zero if the expected change fields are absent.
        weekly_change = numbers[6] - numbers[7] if len(numbers) > 7 else 0
        return {
            "source": "cftc",
            "market": "Euro FX",
            "net_position": net_position,
            "weekly_change": weekly_change,
            "as_of": "latest public CFTC report",
        }
    return None


def _is_int(value: str) -> bool:
    try:
        int(value.replace(",", ""))
        return True
    except ValueError:
        return False


def _mock_cot() -> Dict[str, Any]:
    return {
        "source": "mock",
        "market": "Euro FX",
        "net_position": 84250,
        "weekly_change": 6150,
        "as_of": "mock latest week",
    }
