"""FRED data adapters for US yields and macro regime data."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

from src.data.fred_catalog import FRED_SERIES


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def get_yield_directions() -> Dict[str, Any]:
    """Return direction for US2Y and US10Y yields."""
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return _mock_yields()

    try:
        us2y = _fetch_fred_series("DGS2", api_key)
        us10y = _fetch_fred_series("DGS10", api_key)
        return {
            "source": "fred",
            "us2y": _series_direction(us2y),
            "us10y": _series_direction(us10y),
        }
    except Exception:
        return _mock_yields()


def get_macro_regime_data() -> Dict[str, Any]:
    """Return grouped macro data from FRED, falling back per series when needed."""
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return _mock_macro_regime_data()

    groups: Dict[str, Dict[str, Any]] = {}
    used_mock = False
    used_fred = False

    for group_name, series_map in FRED_SERIES.items():
        groups[group_name] = {}
        for label, series_id in series_map.items():
            try:
                points = _fetch_fred_points(series_id, api_key)
                groups[group_name][label] = _points_direction(series_id, points, source="fred")
                used_fred = True
            except Exception:
                groups[group_name][label] = _mock_macro_point(group_name, label, series_id)
                used_mock = True

    if used_fred and used_mock:
        source = "fred + mock fallback"
    elif used_fred:
        source = "fred"
    else:
        source = "mock"

    return {"source": source, "groups": groups}


def _fetch_fred_series(series_id: str, api_key: str) -> pd.Series:
    points = _fetch_fred_points(series_id, api_key)
    values = [point["value"] for point in points]
    return pd.Series(values)


def _fetch_fred_points(series_id: str, api_key: str, limit: int = 8) -> List[Dict[str, Any]]:
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
    return {
        "series_id": series_id,
        "source": source,
        "latest": latest_value,
        "previous": previous_value,
        "direction": direction,
        "date": latest.get("date", ""),
        "previous_date": previous.get("date", ""),
    }


def _mock_yields() -> Dict[str, Any]:
    return {
        "source": "mock",
        "us2y": {"latest": 4.62, "previous": 4.68, "direction": "falling"},
        "us10y": {"latest": 4.28, "previous": 4.24, "direction": "rising"},
    }


def _mock_macro_regime_data() -> Dict[str, Any]:
    groups: Dict[str, Dict[str, Any]] = {}
    for group_name, series_map in FRED_SERIES.items():
        groups[group_name] = {}
        for label, series_id in series_map.items():
            groups[group_name][label] = _mock_macro_point(group_name, label, series_id)
    return {"source": "mock", "groups": groups}


def _mock_macro_point(group_name: str, label: str, series_id: str) -> Dict[str, Any]:
    mock_values = {
        "DFF": (4.33, 4.33),
        "EFFR": (4.33, 4.33),
        "DFEDTARU": (4.50, 4.50),
        "DFEDTARL": (4.25, 4.25),
        "DGS3MO": (4.40, 4.42),
        "DGS1": (4.12, 4.18),
        "DGS2": (4.20, 4.05),
        "DGS5": (4.32, 4.25),
        "DGS10": (4.49, 4.43),
        "DGS30": (4.98, 4.92),
        "CPIAUCSL": (319.10, 318.90),
        "PCEPI": (126.20, 126.05),
        "CORESTICKM159SFRBATL": (3.40, 3.50),
        "PAYEMS": (159900.0, 159760.0),
        "UNRATE": (4.10, 4.00),
        "ICSA": (245000.0, 238000.0),
        "WALCL": (6740000.0, 6760000.0),
        "SOFR": (4.32, 4.31),
        "DTWEXBGS": (122.2, 121.8),
        "GDP": (29962.0, 29698.0),
        "RSAFS": (728000.0, 725000.0),
        "INDPRO": (103.2, 103.0),
    }
    latest, previous = mock_values.get(series_id, (1.0, 1.0))
    if latest > previous:
        direction = "rising"
    elif latest < previous:
        direction = "falling"
    else:
        direction = "flat"
    return {
        "series_id": series_id,
        "source": "mock",
        "latest": latest,
        "previous": previous,
        "direction": direction,
        "date": "mock latest",
        "previous_date": "mock previous",
        "group": group_name,
        "label": label,
    }
