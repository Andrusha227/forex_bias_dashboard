import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scratch.backtest_data import load_cached_data
from src.engine.bias_engine import score_monthly, score_weekly, score_total
from src.engine.macro_engine import score_macro_regime
from src.engine.scoring import CategoryResult
from src.utils.time import NEW_YORK_TZ

def get_point_in_time_fred_point(series_id, observations, t_str):
    """Filters FRED observations up to t_str and returns latest & previous values."""
    # Observations are list of dicts: {'date': '2021-01-01', 'value': 0.09, 'realtime_start': '2021-01-01', ...}
    # We filter for realtime_start <= t_str
    valid = []
    for obs in observations:
        if obs["realtime_start"] <= t_str:
            valid.append(obs)
            
    if not valid:
        return None
        
    df = pd.DataFrame(valid)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    if df.empty:
        return None
    # Pick the latest revision for each observation date (date)
    # Sort by date and realtime_start so we can group and pick the last
    df = df.sort_values(by=["date", "realtime_start"])
    df_pit = df.groupby("date").last().reset_index()
    
    # Sort by date ascending
    df_pit = df_pit.sort_values("date").reset_index(drop=True)
    
    # Convert to list of dicts and transform
    pit_list = df_pit[["date", "value"]].to_dict(orient="records")
    from src.data.fred_data import _transform_points
    pit_list = _transform_points(series_id, pit_list)
    
    if len(pit_list) < 2:
        return None
        
    latest_row = pit_list[-1]
    prev_row = pit_list[-2]
    
    latest_val = float(latest_row["value"])
    prev_val = float(prev_row["value"])
    
    if latest_val > prev_val:
        direction = "rising"
    elif latest_val < prev_val:
        direction = "falling"
    else:
        direction = "flat"
        
    latest_date_str = latest_row["date"]
    matching_rows = df[df["date"] == latest_date_str]
    timestamp = matching_rows["realtime_start"].max() if not matching_rows.empty else t_str
        
    return {
        "series_id": series_id,
        "source": "fred",
        "latest": latest_val,
        "previous": prev_val,
        "direction": direction,
        "date": latest_date_str,
        "timestamp": timestamp,
        "freshness": "fresh",
    }

def get_point_in_time_yield_spread(fred_data, t_str):
    """Calculates DGS10 - DGS2 spread historically up to t_str."""
    dgs10_obs = fred_data.get("DGS10", [])
    dgs2_obs = fred_data.get("DGS2", [])
    
    valid_10 = [o for o in dgs10_obs if o["realtime_start"] <= t_str]
    valid_2 = [o for o in dgs2_obs if o["realtime_start"] <= t_str]
    
    if not valid_10 or not valid_2:
        return None
        
    df_10 = pd.DataFrame(valid_10)
    df_10["value"] = pd.to_numeric(df_10["value"], errors="coerce")
    df_10 = df_10.dropna(subset=["value"]).sort_values(by=["date", "realtime_start"]).groupby("date").last().reset_index()
    
    df_2 = pd.DataFrame(valid_2)
    df_2["value"] = pd.to_numeric(df_2["value"], errors="coerce")
    df_2 = df_2.dropna(subset=["value"]).sort_values(by=["date", "realtime_start"]).groupby("date").last().reset_index()
    
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
        return None
        
    latest_row = merged.iloc[-1]
    prev_row = merged.iloc[-2]
    
    current_spread = float(latest_row["spread"])
    prev_spread = float(prev_row["spread"])
    
    if current_spread > prev_spread:
        direction = "steepening"
    elif current_spread < prev_spread:
        direction = "flattening"
    else:
        direction = "flat"
        
    return {
        "source": "fred",
        "current_spread": round(current_spread, 4),
        "previous_spread": round(prev_spread, 4),
        "direction": direction,
        "timestamp": latest_row["date"].strftime("%Y-%m-%d"),
        "freshness": "fresh",
    }

def get_point_in_time_net_liquidity(fred_data, t_str):
    """Calculates Net Liquidity historically up to t_str."""
    walcl_obs = fred_data.get("WALCL", [])
    wtregen_obs = fred_data.get("WTREGEN", [])
    rrp_obs = fred_data.get("RRPONTSYD", [])
    
    valid_walcl = [o for o in walcl_obs if o["realtime_start"] <= t_str]
    valid_wtregen = [o for o in wtregen_obs if o["realtime_start"] <= t_str]
    valid_rrp = [o for o in rrp_obs if o["realtime_start"] <= t_str]
    
    if not valid_walcl or not valid_wtregen or not valid_rrp:
        return None
        
    df_walcl = pd.DataFrame(valid_walcl)
    df_walcl["value"] = pd.to_numeric(df_walcl["value"], errors="coerce")
    df_walcl = df_walcl.dropna(subset=["value"]).sort_values(by=["date", "realtime_start"]).groupby("date").last().reset_index()
    
    df_wtregen = pd.DataFrame(valid_wtregen)
    df_wtregen["value"] = pd.to_numeric(df_wtregen["value"], errors="coerce")
    df_wtregen = df_wtregen.dropna(subset=["value"]).sort_values(by=["date", "realtime_start"]).groupby("date").last().reset_index()
    
    df_rrp = pd.DataFrame(valid_rrp)
    df_rrp["value"] = pd.to_numeric(df_rrp["value"], errors="coerce")
    df_rrp = df_rrp.dropna(subset=["value"]).sort_values(by=["date", "realtime_start"]).groupby("date").last().reset_index()
    
    df_walcl["date"] = pd.to_datetime(df_walcl["date"])
    df_wtregen["date"] = pd.to_datetime(df_wtregen["date"])
    df_rrp["date"] = pd.to_datetime(df_rrp["date"])
    
    df_walcl = df_walcl.sort_values("date")
    df_wtregen = df_wtregen.sort_values("date")
    df_rrp = df_rrp.sort_values("date")
    
    merged = pd.merge_asof(
        df_walcl,
        df_wtregen,
        on="date",
        suffixes=("_walcl", "_wtregen"),
        direction="backward"
    )
    merged = pd.merge_asof(
        merged,
        df_rrp,
        on="date",
        direction="backward"
    )
    merged.rename(columns={"value": "value_rrp"}, inplace=True)
    merged = merged.dropna(subset=["value_walcl", "value_wtregen", "value_rrp"])
    
    merged["net_liquidity"] = merged["value_walcl"] - merged["value_wtregen"] - (merged["value_rrp"] * 1000.0)
    
    if len(merged) < 2:
        return None
        
    latest_row = merged.iloc[-1]
    prev_row = merged.iloc[-2]
    
    current_liq = float(latest_row["net_liquidity"])
    prev_liq = float(prev_row["net_liquidity"])
    
    if current_liq > prev_liq:
        direction = "rising"
    elif current_liq < prev_liq:
        direction = "falling"
    else:
        direction = "flat"
        
    return {
        "source": "fred",
        "current": round(current_liq, 2),
        "previous": round(prev_liq, 2),
        "direction": direction,
        "timestamp": latest_row["date"].strftime("%Y-%m-%d"),
        "freshness": "fresh",
    }

def get_point_in_time_cot(cot_df, t_str):
    """Get latest COT position available at t_str (released on Friday for Tuesday)."""
    # Release date is as_of_date + 3 days
    cot_df = cot_df.copy()
    cot_df["as_of_date"] = pd.to_datetime(cot_df["as_of_date"])
    cot_df["release_date"] = cot_df["as_of_date"] + pd.Timedelta(days=3)
    
    # Filter for release_date <= t_str
    t_dt = pd.to_datetime(t_str)
    valid = cot_df[cot_df["release_date"] <= t_dt]
    if valid.empty:
        return None
        
    latest_cot = valid.iloc[-1]
    
    return {
        "source": "cftc",
        "market": "Euro FX",
        "net_position": int(latest_cot["net_position"]),
        "weekly_change": int(latest_cot["weekly_change"]),
        "as_of": latest_cot["as_of_date"].strftime("%Y-%m-%d"),
        "timestamp": latest_cot["release_date"].strftime("%Y-%m-%d"),
        "freshness": "fresh",
    }

def get_point_in_time_dxy(dxy_df, t_str):
    """Calculates DXY momentum direction as of t_str."""
    dxy_df = dxy_df[dxy_df["date"] <= t_str].sort_values("date").reset_index(drop=True)
    if len(dxy_df) < 6:
        return None
        
    latest = float(dxy_df.iloc[-1]["close"])
    previous = float(dxy_df.iloc[-6]["close"])
    
    if latest > previous:
        direction = "rising"
    elif latest < previous:
        direction = "falling"
    else:
        direction = "flat"
        
    return {
        "source": "stooq", # compatibility
        "direction": direction,
        "latest": latest,
        "previous": previous,
        "timestamp": dxy_df.iloc[-1]["date"],
        "freshness": "fresh",
    }

def build_point_in_time_monthly_range(eurusd_df, t_str):
    """Builds Monthly Open Range dictionary point-in-time up to t_str."""
    dated = eurusd_df[eurusd_df["date"] <= t_str].copy()
    if dated.empty:
        return {}
        
    dated["session_date"] = pd.to_datetime(dated["date"])
    latest_date = dated.iloc[-1]["session_date"]
    
    month_rows = dated[dated["session_date"].dt.to_period("M") == latest_date.to_period("M")]
    if month_rows.empty:
        return {}
        
    first_trade = month_rows.iloc[0]
    d_open = float(first_trade["open"])
    d_high = float(first_trade["high"])
    d_low = float(first_trade["low"])
    d_time_utc = first_trade["date"]
    first_trade_date = first_trade["session_date"]
    
    first_week_start = first_trade_date - pd.Timedelta(days=first_trade_date.weekday())
    first_week_end = first_week_start + pd.Timedelta(days=6)
    first_week_rows = dated[(dated["session_date"] >= first_week_start) & (dated["session_date"] <= first_week_end)]
    
    if not first_week_rows.empty:
        w_open = float(first_week_rows.iloc[0]["open"])
        w_high = float(first_week_rows["high"].max())
        w_low = float(first_week_rows["low"].min())
        w_time_utc = first_week_rows.iloc[0]["date"]
    else:
        w_open, w_high, w_low, w_time_utc = d_open, d_high, d_low, d_time_utc
        
    first_week_subsequent = first_week_rows[first_week_rows["session_date"] > first_trade_date]
    d_swept_during_first_week = False
    if not first_week_subsequent.empty:
        d_swept_high = float(first_week_subsequent["high"].max()) > d_high
        d_swept_low = float(first_week_subsequent["low"].min()) < d_low
        d_swept_during_first_week = d_swept_high or d_swept_low
        
    is_after_first_week = latest_date > first_week_end
    active_source = "W" if (is_after_first_week and d_swept_during_first_week) else "D"
    
    return {
        "d_open": {
            "open": d_open,
            "high": d_high,
            "low": d_low,
            "time_utc": pd.to_datetime(d_time_utc),
            "label": "First Day of Month (D)"
        },
        "w_open": {
            "open": w_open,
            "high": w_high,
            "low": w_low,
            "time_utc": pd.to_datetime(w_time_utc),
            "label": "First Week of Month (W)"
        },
        "d_swept_during_first_week": d_swept_during_first_week,
        "is_after_first_week": is_after_first_week,
        "active_source": active_source,
        "freshness": "fresh",
        "timestamp": latest_date.strftime("%Y-%m-%d")
    }

def build_point_in_time_weekly_range_h4(h4_df, eurusd_df, t_str):
    """Builds Monday H4 / Daily Weekly Open Range transitional structure up to t_str."""
    # First, daily Monday open candle
    dated = eurusd_df[eurusd_df["date"] <= t_str].copy()
    if dated.empty:
        return {}
        
    dated["session_date"] = pd.to_datetime(dated["date"])
    latest_date = dated.iloc[-1]["session_date"]
    
    week_start = latest_date - pd.Timedelta(days=latest_date.weekday())
    monday_daily_rows = dated[dated["session_date"] == week_start]
    
    monday_d = None
    if not monday_daily_rows.empty:
        first_row = monday_daily_rows.iloc[0]
        monday_d = {
            "open": float(first_row["open"]),
            "high": float(first_row["high"]),
            "low": float(first_row["low"]),
            "time_utc": pd.to_datetime(first_row["date"]),
            "label": "Monday Daily Candle (D)"
        }
        
    # If no H4, fallback to daily Monday range
    if h4_df is None or h4_df.empty:
        return {
            "monday_d": monday_d,
            "monday_4h_swept": False,
            "is_after_monday": latest_date > week_start,
            "active_source": "D",
            "freshness": "fresh",
            "timestamp": latest_date.strftime("%Y-%m-%d")
        }
        
    # Process H4 history up to t_str
    # Twelve Data timestamps are in UTC in our fetch, but let's check
    h4_valid = h4_df[h4_df["datetime"] <= t_str].copy()
    h4_valid["date"] = pd.to_datetime(h4_valid["datetime"])
    
    # Re-apply the build_weekly_open_ranges_from_h4 logic point-in-time
    h4_valid["time_ny"] = h4_valid["date"].dt.tz_localize("UTC").dt.tz_convert(NEW_YORK_TZ)
    if h4_valid.empty:
        return {
            "monday_d": monday_d,
            "monday_4h_swept": False,
            "is_after_monday": latest_date > week_start,
            "active_source": "D",
            "freshness": "fresh",
            "timestamp": latest_date.strftime("%Y-%m-%d")
        }
        
    latest_ny = h4_valid.iloc[-1]["time_ny"]
    # Week start in NY time
    week_start_ny = pd.Timestamp(latest_ny.date()) - pd.Timedelta(days=latest_ny.weekday())
    week_start_ny = week_start_ny.tz_localize(NEW_YORK_TZ)
    sunday_session_start = week_start_ny - pd.Timedelta(hours=7)
    
    sunday_rows = h4_valid[(h4_valid["time_ny"] >= sunday_session_start) & (h4_valid["time_ny"] < week_start_ny)].sort_values("date")
    monday_rows = h4_valid[
        (h4_valid["time_ny"].dt.date == week_start_ny.date())
        & (h4_valid["time_ny"].dt.hour >= 1)
        & (h4_valid["time_ny"].dt.hour < 5)
    ].sort_values("date")
    
    def _range_from_first_row(frame, label):
        if frame.empty:
            return None
        first = frame.iloc[0]
        return {
            "source": "twelve data",
            "open": float(first["open"]),
            "high": float(first["high"]),
            "low": float(first["low"]),
            "time_utc": first["date"].to_pydatetime(),
            "time_ny": first["time_ny"].to_pydatetime(),
            "label": f"{label} ({first['time_ny'].strftime('%a %H:%M')} NY)",
        }
        
    sunday_open = _range_from_first_row(sunday_rows, "Sunday session weekly open range")
    monday_open = _range_from_first_row(monday_rows, "Monday 01:00 NY first H4 weekly range")
    
    monday_4h_swept = False
    if monday_d and monday_open:
        monday_d_high = float(monday_d["high"])
        monday_d_low = float(monday_d["low"])
        monday_4h_high = float(monday_open["high"])
        monday_4h_low = float(monday_open["low"])
        monday_4h_swept = (monday_d_high > monday_4h_high) or (monday_d_low < monday_4h_low)
        
    is_after_monday = latest_date > week_start
    active_weekly_source = "D" if (is_after_monday and not monday_4h_swept) else "4H"
    
    return {
        "sunday_open": sunday_open,
        "monday_open": monday_open,
        "monday_d": monday_d,
        "monday_4h_swept": monday_4h_swept,
        "is_after_monday": is_after_monday,
        "active_source": active_weekly_source,
        "freshness": "fresh",
        "timestamp": latest_date.strftime("%Y-%m-%d")
    }

def run_score_on_date(cache, t_str, use_h4=True):
    """Runs the scoring engine at the close of date t_str."""
    t_str = pd.Timestamp(t_str).strftime("%Y-%m-%d")
    eurusd_df = cache["eurusd"]
    dxy_df = cache["dxy"]
    h4_df = cache["h4"] if use_h4 else None
    cot_df = cache["cot"]
    fred_data = cache["fred"]
    
    # 1. Price context
    day_rows = eurusd_df[eurusd_df["date"] <= t_str].sort_values("date")
    if day_rows.empty:
        return None
    latest_candle = day_rows.iloc[-1]
    
    # Calculate previous week high/low up to t_str
    latest_date = pd.Timestamp(latest_candle["date"])
    week_start = latest_date.normalize() - pd.Timedelta(days=latest_date.weekday())
    previous_week_rows = day_rows[
        (pd.to_datetime(day_rows["date"]) >= week_start - pd.Timedelta(days=7)) & 
        (pd.to_datetime(day_rows["date"]) < week_start)
    ]
    if not previous_week_rows.empty:
        prev_week_high = float(previous_week_rows["high"].max())
        prev_week_low = float(previous_week_rows["low"].min())
    else:
        # Fallback to previous candles
        prev_week_high = float(latest_candle["high"])
        prev_week_low = float(latest_candle["low"])
        
    current_price = float(latest_candle["close"])
    
    # Monthly Range
    monthly_ranges = build_point_in_time_monthly_range(eurusd_df, t_str)
    
    # Weekly Range
    weekly_ranges = build_point_in_time_weekly_range_h4(h4_df, eurusd_df, t_str)
    
    # COT
    cot = get_point_in_time_cot(cot_df, t_str)
    
    # DXY
    dxy = get_point_in_time_dxy(dxy_df, t_str)
    
    monthly_context = {
        "current_price": current_price,
        "monthly_open": monthly_ranges["d_open"]["open"] if monthly_ranges.get("d_open") else current_price,
        "monthly_open_ranges": monthly_ranges,
        "h4_history": None, # Force using history
        "history": day_rows,
        "cot_net_position": cot["net_position"] if cot else None,
        "cot_weekly_change": cot["weekly_change"] if cot else None,
        "cot_metadata": cot,
        "eurusd_metadata": {"timestamp": t_str, "source": "yahoo", "freshness": "fresh"},
    }
    
    weekly_context = {
        "current_price": current_price,
        "weekly_open": weekly_ranges["monday_d"]["open"] if weekly_ranges.get("monday_d") else current_price,
        "weekly_open_ranges": weekly_ranges,
        "h4_history": None, # Force using history for sweeps checks in monthly/weekly engines
        "history": day_rows,
        "dxy_direction": dxy["direction"] if dxy else None,
        "dxy_metadata": dxy,
        "eurusd_metadata": {"timestamp": t_str, "source": "yahoo", "freshness": "fresh"},
    }
    
    # FRED Macro indicators point-in-time
    macro_points = {}
    from src.data.fred_catalog import FRED_SERIES
    for group_name, series_map in FRED_SERIES.items():
        macro_points[group_name] = {}
        for label, series_id in series_map.items():
            obs = fred_data.get(series_id, [])
            macro_points[group_name][label] = get_point_in_time_fred_point(series_id, obs, t_str)
            
    macro_context = {
        "source": "fred",
        "groups": macro_points
    }
    
    yield_spread = get_point_in_time_yield_spread(fred_data, t_str)
    net_liquidity = get_point_in_time_net_liquidity(fred_data, t_str)
    
    # Score Monthly Category
    monthly_cat = score_monthly(monthly_context)
    
    # Score Weekly Category
    weekly_cat = score_weekly(weekly_context)
    
    # Score Macro Regime
    macro_result = score_macro_regime(
        macro_context,
        yield_spread=yield_spread,
        net_liquidity=net_liquidity
    )
    macro_categories = macro_result["categories"]
    
    # Combine everything
    all_categories = [monthly_cat, weekly_cat] + macro_categories
    total = score_total(all_categories)
    
    return {
        "date": t_str,
        "close_price": current_price,
        "normalized_score": total.get("normalized_score"),
        "verdict": total.get("verdict"),
        "categories": total.get("categories"),
        "total": total
    }
