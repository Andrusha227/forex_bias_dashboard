"""FRED data adapters for US yields, macro regime data, and derived indicators."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

from src.data.fred_catalog import FRED_SERIES


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def get_yield_directions() -> Optional[Dict[str, Any]]:
    """Return direction for US2Y and US10Y yields.

    Returns None when the FRED API key is missing or the API call fails.
    """
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None

    try:
        us2y = _fetch_fred_series("DGS2", api_key)
        us10y = _fetch_fred_series("DGS10", api_key)
        return {
            "source": "fred",
            "us2y": _series_direction(us2y),
            "us10y": _series_direction(us10y),
        }
    except Exception:
        return None


def get_macro_regime_data() -> Dict[str, Any]:
    """Return grouped macro data from FRED.

    Each individual series that fails is set to None in its group dict
    rather than fabricating mock values.
    """
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return {"source": "unavailable", "groups": {}}

    groups: Dict[str, Dict[str, Any]] = {}
    any_success = False

    for group_name, series_map in FRED_SERIES.items():
        groups[group_name] = {}
        for label, series_id in series_map.items():
            try:
                points = _fetch_fred_points(series_id, api_key)
                points = _transform_points(series_id, points)
                groups[group_name][label] = _points_direction(series_id, points, source="fred")
                any_success = True
            except Exception:
                groups[group_name][label] = None

    source = "fred" if any_success else "unavailable"
    return {"source": source, "groups": groups}


def get_yield_spread() -> Optional[Dict[str, Any]]:
    """Fetch DGS10 and DGS2, return the 10Y-2Y yield spread with direction.

    Returns {source, current_spread, previous_spread, direction, timestamp, freshness} or None.
    """
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None

    try:
        dgs10_points = _fetch_fred_points("DGS10", api_key, limit=15)
        dgs2_points = _fetch_fred_points("DGS2", api_key, limit=15)

        df_10 = pd.DataFrame(dgs10_points)
        df_2 = pd.DataFrame(dgs2_points)

        df_10["date"] = pd.to_datetime(df_10["date"])
        df_2["date"] = pd.to_datetime(df_2["date"])

        df_10 = df_10.sort_values("date")
        df_2 = df_2.sort_values("date")

        merged = pd.merge_asof(
            df_10,
            df_2,
            on="date",
            suffixes=("_10", "_2"),
            direction="backward"
        )
        merged["spread"] = merged["value_10"] - merged["value_2"]
        merged = merged.dropna(subset=["spread"])

        if len(merged) < 2:
            raise ValueError("Not enough aligned points for yield spread")

        current_row = merged.iloc[-1]
        previous_row = merged.iloc[-2]

        current_spread = float(current_row["spread"])
        previous_spread = float(previous_row["spread"])

        if current_spread > previous_spread:
            direction = "steepening"
        elif current_spread < previous_spread:
            direction = "flattening"
        else:
            direction = "flat"

        current_date_str = current_row["date"].strftime("%Y-%m-%d")
        
        # Freshness calculation
        from datetime import datetime, timezone
        age_days = (datetime.now(timezone.utc).date() - current_row["date"].date()).days
        freshness = "fresh" if age_days <= 10 else "stale"

        return {
            "source": "fred",
            "current_spread": round(current_spread, 4),
            "previous_spread": round(previous_spread, 4),
            "direction": direction,
            "timestamp": current_date_str,
            "freshness": freshness,
        }
    except Exception:
        return None


def get_net_liquidity() -> Optional[Dict[str, Any]]:
    """Fetch WALCL, WTREGEN, RRPONTSYD and calculate net liquidity.

    Net Liquidity = WALCL - WTREGEN - RRPONTSYD

    Returns {source, current, previous, direction, timestamp, freshness} or None.
    """
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None

    try:
        walcl = _fetch_fred_points("WALCL", api_key, limit=8)
        wtregen = _fetch_fred_points("WTREGEN", api_key, limit=40)
        rrpontsyd = _fetch_fred_points("RRPONTSYD", api_key, limit=40)

        df_walcl = pd.DataFrame(walcl)
        df_wtregen = pd.DataFrame(wtregen)
        df_rrpontsyd = pd.DataFrame(rrpontsyd)

        df_walcl["date"] = pd.to_datetime(df_walcl["date"])
        df_wtregen["date"] = pd.to_datetime(df_wtregen["date"])
        df_rrpontsyd["date"] = pd.to_datetime(df_rrpontsyd["date"])

        df_walcl = df_walcl.sort_values("date")
        df_wtregen = df_wtregen.sort_values("date")
        df_rrpontsyd = df_rrpontsyd.sort_values("date")

        merged = pd.merge_asof(
            df_walcl,
            df_wtregen,
            on="date",
            suffixes=("_walcl", "_wtregen"),
            direction="backward"
        )
        merged = pd.merge_asof(
            merged,
            df_rrpontsyd,
            on="date",
            direction="backward"
        )
        merged.rename(columns={"value": "value_rrpontsyd"}, inplace=True)
        merged = merged.dropna(subset=["value_walcl", "value_wtregen", "value_rrpontsyd"])

        # RRPONTSYD is in Billions, WALCL/WTREGEN are in Millions. Align to Millions.
        merged["net_liquidity"] = merged["value_walcl"] - merged["value_wtregen"] - (merged["value_rrpontsyd"] * 1000.0)

        if len(merged) < 2:
            raise ValueError("Not enough aligned points for net liquidity")

        current_row = merged.iloc[-1]
        previous_row = merged.iloc[-2]

        current = float(current_row["net_liquidity"])
        previous = float(previous_row["net_liquidity"])

        if current > previous:
            direction = "rising"
        elif current < previous:
            direction = "falling"
        else:
            direction = "flat"

        current_date_str = current_row["date"].strftime("%Y-%m-%d")

        from datetime import datetime, timezone
        age_days = (datetime.now(timezone.utc).date() - current_row["date"].date()).days
        freshness = "fresh" if age_days <= 10 else "stale"

        return {
            "source": "fred",
            "current": round(current, 2),
            "previous": round(previous, 2),
            "direction": direction,
            "timestamp": current_date_str,
            "freshness": freshness,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_fred_series(series_id: str, api_key: str) -> pd.Series:
    points = _fetch_fred_points(series_id, api_key)
    values = [point["value"] for point in points]
    return pd.Series(values)


def _fetch_fred_points(series_id: str, api_key: str, limit: int = 24) -> List[Dict[str, Any]]:
    response = requests.get(
        FRED_OBSERVATIONS_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=8,
    )
    response.raise_for_status()
    observations = response.json().get("observations", [])
    points = []
    for item in observations:
        value = item.get("value")
        if value and value != ".":
            points.append({"date": item.get("date", ""), "value": float(value)})

    if len(points) < 2:
        raise ValueError(f"Not enough FRED observations for {series_id}")

    return list(reversed(points))


def _transform_points(series_id: str, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform raw index levels into YoY or MoM rates where appropriate."""
    if series_id in ("CPIAUCSL", "PCEPI", "CORESTICKM159SFRBATL", "RSAFS", "INDPRO"):
        # YoY change (12 months lag)
        transformed = []
        for i in range(12, len(points)):
            val_now = points[i]["value"]
            val_past = points[i - 12]["value"]
            if val_past != 0:
                yoy = (val_now - val_past) / val_past * 100.0
                transformed.append({"date": points[i]["date"], "value": yoy})
        return transformed
        
    elif series_id == "GDP":
        # YoY change (4 quarters lag)
        transformed = []
        for i in range(4, len(points)):
            val_now = points[i]["value"]
            val_past = points[i - 4]["value"]
            if val_past != 0:
                yoy = (val_now - val_past) / val_past * 100.0
                transformed.append({"date": points[i]["date"], "value": yoy})
        return transformed
        
    elif series_id == "PAYEMS":
        # MoM Change vs 3-month SMA
        mom_changes = []
        for i in range(1, len(points)):
            change = points[i]["value"] - points[i - 1]["value"]
            mom_changes.append({"date": points[i]["date"], "value": change})
            
        if len(mom_changes) >= 3:
            change_t = mom_changes[-1]["value"]
            change_t_1 = mom_changes[-2]["value"]
            change_t_2 = mom_changes[-3]["value"]
            sma_t = (change_t + change_t_1 + change_t_2) / 3.0
            
            return [
                {"date": mom_changes[-1]["date"], "value": sma_t},
                {"date": mom_changes[-1]["date"], "value": change_t}
            ]
        return mom_changes
        
    return points


def _series_direction(series: pd.Series) -> Dict[str, Any]:
    latest = float(series.iloc[-1])
    previous = float(series.iloc[-2])
    if latest > previous:
        direction = "rising"
    elif latest < previous:
        direction = "falling"
    else:
        direction = "flat"
    return {"latest": latest, "previous": previous, "direction": direction}


def _points_direction(series_id: str, points: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
    latest = points[-1]
    previous = points[-2]
    latest_value = float(latest["value"])
    previous_value = float(previous["value"])
    if latest_value > previous_value:
        direction = "rising"
    elif latest_value < previous_value:
        direction = "falling"
    else:
        direction = "flat"

    from datetime import datetime, timezone
    try:
        latest_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
        age_days = (datetime.now(timezone.utc).date() - latest_date).days
        
        # Freshness thresholds based on series_id
        if series_id == "GDP":
            threshold = 130
        elif series_id in ("CPIAUCSL", "PCEPI", "CORESTICKM159SFRBATL", "PAYEMS", "UNRATE", "RSAFS", "INDPRO"):
            threshold = 45
        elif series_id == "ICSA":
            threshold = 10
        else:
            threshold = 10  # DFF, yield series, etc.
            
        freshness = "fresh" if age_days <= threshold else "stale"
    except Exception:
        freshness = "unknown"

    return {
        "series_id": series_id,
        "source": source,
        "latest": latest_value,
        "previous": previous_value,
        "direction": direction,
        "date": latest.get("date", ""),
        "previous_date": previous.get("date", ""),
        "timestamp": latest.get("date", ""),
        "freshness": freshness,
    }
