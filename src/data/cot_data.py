"""CFTC COT adapter for Euro FX — returns None when unavailable."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import requests


import csv
from io import StringIO
from datetime import datetime, timezone

CFTC_CURRENT_LEGACY_URL = "https://www.cftc.gov/dea/newcot/deafut.txt"


def get_euro_fx_cot() -> Optional[Dict[str, Any]]:
    """Return Euro FX non-commercial net position and weekly change.

    The parser targets the public CFTC legacy text report. If the format changes
    or the network is unavailable, None is returned.
    """
    try:
        response = requests.get(
            CFTC_CURRENT_LEGACY_URL,
            timeout=10,
            headers={"User-Agent": "forex_bias_dashboard/0.1"},
        )
        response.raise_for_status()
        parsed = _parse_legacy_report(response.text)
        if parsed is None:
            raise ValueError("Euro FX COT row was not found")
        return parsed
    except Exception:
        return None


def _parse_legacy_report(text: str) -> Optional[Dict[str, Any]]:
    reader = csv.reader(StringIO(text))
    for row in reader:
        if not row or row[0].strip() != "EURO FX - CHICAGO MERCANTILE EXCHANGE":
            continue

        try:
            non_commercial_long = int(row[8].strip())
            non_commercial_short = int(row[9].strip())
            net_position = non_commercial_long - non_commercial_short

            change_long = int(row[38].strip())
            change_short = int(row[39].strip())
            weekly_change = change_long - change_short

            as_of_str = row[2].strip()
            as_of_date = datetime.strptime(as_of_str, "%Y-%m-%d").date()
            
            # Freshness calculation
            age_days = (datetime.now(timezone.utc).date() - as_of_date).days
            freshness = "fresh" if age_days <= 10 else "stale"

            return {
                "source": "cftc",
                "market": "Euro FX",
                "net_position": net_position,
                "weekly_change": weekly_change,
                "as_of": as_of_str,
                "timestamp": as_of_str,
                "freshness": freshness,
            }
        except (IndexError, ValueError):
            continue
    return None
