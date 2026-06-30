"""Streamlit app for the EUR/USD Macro Bias Dashboard."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.data.calendar_data import get_high_impact_events_today
from src.data.cot_data import get_euro_fx_cot
from src.data.fred_data import get_macro_regime_data, get_yield_directions
from src.data.market_data import get_dxy_direction, get_eurusd_snapshot
from src.engine.bias_engine import score_intraday, score_monthly, score_total, score_weekly
from src.engine.macro_engine import score_macro_regime
from src.engine.opening_engine import analyze_opening_range
from src.utils.time import BERLIN_TZ


def main() -> None:
    """Render the Streamlit dashboard."""
    load_dotenv()

    st.set_page_config(
        page_title="EUR/USD Macro Bias Dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_styles()

    st.title("EUR/USD Macro Bias Dashboard")
    st.warning("This is a decision-support dashboard, not a trading signal.")

    with st.spinner("Loading market context..."):
        context = _load_context()
    context = _apply_sidebar_overrides(context)

    monthly_score = score_monthly(context["monthly"])
    weekly_score = score_weekly(context["weekly"])
    intraday_score = score_intraday(context["intraday"])
    macro_score = score_macro_regime(context["macro"])
    total_score = score_total(monthly_score, weekly_score, intraday_score, macro_score)
    opening_context = _build_opening_context(context["eurusd"], total_score)

    _render_final_bias(total_score)
    _render_price_chart(context["eurusd"])

    col_monthly, col_weekly, col_intraday = st.columns(3)
    with col_monthly:
        _render_monthly_card(context, monthly_score)
    with col_weekly:
        _render_weekly_card(context, weekly_score, opening_context)
    with col_intraday:
        _render_intraday_card(context, intraday_score, opening_context)

    _render_macro_regime(context, macro_score)
    _render_sources(context)


@st.cache_data(ttl=900, show_spinner=False)
def _load_context() -> Dict[str, Any]:
    """Load all data sources with graceful fallback handled by adapters."""
    eurusd = get_eurusd_snapshot()
    cot = get_euro_fx_cot()
    dxy = get_dxy_direction()
    yields = get_yield_directions()
    macro = get_macro_regime_data()
    calendar = get_high_impact_events_today()

    monthly = {
        "current_price": eurusd["current_price"],
        "monthly_open": eurusd["monthly_open"],
        "monthly_open_ranges": eurusd.get("monthly_open_ranges"),
        "h4_history": eurusd.get("h4_history"),
        "history": eurusd.get("history"),
        "cot_net_position": cot["net_position"],
        "cot_weekly_change": cot["weekly_change"],
    }
    weekly = {
        "current_price": eurusd["current_price"],
        "weekly_open": eurusd["weekly_open"],
        "weekly_open_ranges": eurusd.get("weekly_open_ranges"),
        "h4_history": eurusd.get("h4_history"),
        "history": eurusd.get("history"),
        "dxy_direction": dxy["direction"],
        "us2y_direction": yields["us2y"]["direction"],
        "us10y_direction": yields["us10y"]["direction"],
    }
    intraday = {
        "current_price": eurusd["current_price"],
        "daily_open": eurusd["daily_open"],
        "daily_open_high": eurusd.get("daily_open_high"),
        "daily_open_low": eurusd.get("daily_open_low"),
        "asia_high": eurusd["asia_high"],
        "asia_low": eurusd["asia_low"],
        "news_within_60m": calendar["news_within_60m"],
    }

    return {
        "eurusd": eurusd,
        "cot": cot,
        "dxy": dxy,
        "yields": yields,
        "macro": macro,
        "calendar": calendar,
        "monthly": monthly,
        "weekly": weekly,
        "intraday": intraday,
    }


def _apply_sidebar_overrides(context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply chart-level overrides before scoring."""
    adjusted = copy.deepcopy(context)
    eurusd = adjusted["eurusd"]

    st.sidebar.header("Chart Levels")
    st.sidebar.caption("Use this when your TradingView 4H Daily Open is more accurate than the fallback feed.")

    override_current = st.sidebar.checkbox("Override current EUR/USD", value=False)
    if override_current:
        current_price = st.sidebar.number_input(
            "Current EUR/USD",
            min_value=0.50000,
            max_value=2.00000,
            value=float(eurusd["current_price"]),
            step=0.00001,
            format="%.5f",
        )
        eurusd["current_price"] = float(current_price)
        adjusted["monthly"]["current_price"] = float(current_price)
        adjusted["weekly"]["current_price"] = float(current_price)
        adjusted["intraday"]["current_price"] = float(current_price)

    override_daily_open = st.sidebar.checkbox("Override Daily Open (DO range)", value=False)
    if override_daily_open:
        daily_open = st.sidebar.number_input(
            "DO open/reference",
            min_value=0.50000,
            max_value=2.00000,
            value=float(eurusd["daily_open"]),
            step=0.00001,
            format="%.5f",
        )
        default_low = float(eurusd.get("daily_open_low") or eurusd["daily_open"])
        default_high = float(eurusd.get("daily_open_high") or eurusd["daily_open"])
        daily_open_low = st.sidebar.number_input(
            "DO low",
            min_value=0.50000,
            max_value=2.00000,
            value=min(default_low, default_high),
            step=0.00001,
            format="%.5f",
        )
        daily_open_high = st.sidebar.number_input(
            "DO high",
            min_value=0.50000,
            max_value=2.00000,
            value=max(default_low, default_high),
            step=0.00001,
            format="%.5f",
        )
        range_low = min(float(daily_open_low), float(daily_open_high))
        range_high = max(float(daily_open_low), float(daily_open_high))
        eurusd["daily_open"] = float(daily_open)
        eurusd["daily_open_low"] = range_low
        eurusd["daily_open_high"] = range_high
        eurusd["daily_open_source"] = "manual chart override"
        eurusd["daily_open_window"] = "Manual DO range from TradingView 4H chart"
        adjusted["intraday"]["daily_open"] = float(daily_open)
        adjusted["intraday"]["daily_open_low"] = range_low
        adjusted["intraday"]["daily_open_high"] = range_high

    return adjusted


def _render_final_bias(total_score: Dict[str, Any]) -> None:
    label = total_score["label"]
    score = total_score["score"]
    if score >= 3:
        css_class = "bullish"
    elif score <= -3:
        css_class = "bearish"
    else:
        css_class = "neutral"

    st.markdown(
        f"""
        <div class="final-bias {css_class}">
            <div class="final-label">{label}</div>
            <div class="final-score">
                Total score: {_fmt_score(score)} | Core: {_fmt_score(total_score.get("core_score", 0))} | Macro: {_fmt_score(total_score.get("macro_score", 0))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_price_chart(eurusd: Dict[str, Any]) -> None:
    history = eurusd.get("history")
    if not isinstance(history, pd.DataFrame) or history.empty:
        return

    chart_data = history.tail(60).copy()
    fig = px.line(chart_data, x="date", y="close", title="EUR/USD Daily Close")
    fig.update_layout(
        height=280,
        margin={"l": 4, "r": 4, "t": 38, "b": 4},
        autosize=True,
        title={"font": {"size": 16}},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_monthly_card(context: Dict[str, Any], score: Dict[str, Any]) -> None:
    eurusd = context["eurusd"]
    cot = context["cot"]
    current_price = eurusd["current_price"]

    # Calculate monthly analysis for UI display
    monthly_open_ranges = eurusd.get("monthly_open_ranges")
    candles = eurusd.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = eurusd.get("history")

    from src.engine.opening_engine import analyze_monthly_opening_range
    monthly_analysis = analyze_monthly_opening_range(float(current_price), monthly_open_ranges, candles)

    _card_header("Monthly Bias", score["score"])
    st.metric("Current EUR/USD", _fmt_price(current_price))

    # Render the Monthly Open chip
    active_source = monthly_analysis.get("active_source", "D")
    _render_opening_range_chip(f"Monthly Open ({active_source})", monthly_analysis)

    st.metric("COT EUR net position", f"{cot['net_position']:,}", f"{cot['weekly_change']:+,} w/w")
    _render_contributions(score["contributions"])


def _render_weekly_card(context: Dict[str, Any], score: Dict[str, Any], opening_context: Dict[str, Any]) -> None:
    eurusd = context["eurusd"]
    dxy = context["dxy"]
    yields = context["yields"]

    _card_header("Weekly Bias", score["score"])
    st.metric("Current EUR/USD", _fmt_price(eurusd["current_price"]))
    _render_weekly_opening_ranges(opening_context)
    st.metric("Previous week high / low", f"{_fmt_price(eurusd['previous_week_high'])} / {_fmt_price(eurusd['previous_week_low'])}")
    st.metric("DXY direction", dxy["direction"].title())
    st.metric("US2Y direction", yields["us2y"]["direction"].title())
    st.metric("US10Y direction", yields["us10y"]["direction"].title())
    _render_contributions(score["contributions"])


def _render_intraday_card(context: Dict[str, Any], score: Dict[str, Any], opening_context: Dict[str, Any]) -> None:
    eurusd = context["eurusd"]
    calendar = context["calendar"]

    _card_header("Intraday Context", score["score"])
    _render_daily_open_status(eurusd, opening_context["daily"])
    _render_trade_filter(opening_context["trade_filter"])
    st.metric("Yesterday high / low", f"{_fmt_price(eurusd['yesterday_high'])} / {_fmt_price(eurusd['yesterday_low'])}")
    st.metric("Asia high / low", f"{_fmt_price(eurusd['asia_high'])} / {_fmt_price(eurusd['asia_low'])}")
    st.metric("London session open", _fmt_price(eurusd["london_open"]))
    st.metric("New York session open", _fmt_price(eurusd["new_york_open"]))

    if calendar["news_within_60m"]:
        st.error("High impact EUR/USD news is within the next 60 minutes.")
    else:
        st.success("No high impact EUR/USD news within the next 60 minutes.")

    if calendar.get("source") == "mock":
        st.warning("Economic calendar provider is unavailable. No real news events loaded.")
    _render_events(calendar["events"])
    if calendar.get("other_high_impact_events"):
        with st.expander("Other high-impact events today"):
            _render_events(calendar["other_high_impact_events"])
    _render_contributions(score["contributions"])


def _build_opening_context(eurusd: Dict[str, Any], total_score: Dict[str, Any]) -> Dict[str, Any]:
    h4 = eurusd.get("h4_history")
    daily_range = None
    if eurusd.get("daily_open_high") is not None and eurusd.get("daily_open_low") is not None:
        daily_range = {
            "open": eurusd["daily_open"],
            "high": eurusd["daily_open_high"],
            "low": eurusd["daily_open_low"],
            "time_utc": eurusd.get("daily_open_time_utc"),
            "label": eurusd.get("daily_open_window", "Daily Open range"),
        }

    daily_analysis = analyze_opening_range(float(eurusd["current_price"]), daily_range, h4)
    weekly_ranges = eurusd.get("weekly_open_ranges") or {}
    sunday_analysis = analyze_opening_range(float(eurusd["current_price"]), weekly_ranges.get("sunday_open"), h4)
    from src.engine.opening_engine import analyze_weekly_opening_range
    weekly_analysis = analyze_weekly_opening_range(float(eurusd["current_price"]), weekly_ranges, h4)
    trade_filter = _daily_open_trade_filter(daily_analysis, total_score)

    return {
        "daily": daily_analysis,
        "weekly_sunday": sunday_analysis,
        "weekly_monday": weekly_analysis,
        "trade_filter": trade_filter,
    }


def _daily_open_trade_filter(daily_analysis: Dict[str, Any], total_score: Dict[str, Any]) -> Dict[str, str]:
    label = str(total_score.get("label", "Neutral / Wait"))
    location = daily_analysis.get("state", "unknown")

    if location == "inside":
        return {
            "css_class": "filter-skip",
            "title": "Skip positions",
            "detail": "Price is inside the Daily Open range. Wait for a clean break or rejection.",
        }

    if label == "Bearish EUR/USD":
        if location == "above":
            return {
                "css_class": "filter-short",
                "title": "Possible short",
                "detail": "Overall context is bearish and price is above the DO range. Watch for rejection back below range.",
            }
        return {
            "css_class": "filter-wait",
            "title": "Short context, no chase",
            "detail": "Price is already below the DO range. Prefer a pullback or retest before looking for shorts.",
        }

    if label == "Bullish EUR/USD":
        if location == "below":
            return {
                "css_class": "filter-long",
                "title": "Possible long",
                "detail": "Overall context is bullish and price is below the DO range. Watch for reclaim back into/above range.",
            }
        return {
            "css_class": "filter-wait",
            "title": "Long context, no chase",
            "detail": "Price is already above the DO range. Prefer a pullback or retest before looking for longs.",
        }

    return {
        "css_class": "filter-wait",
        "title": "Wait",
        "detail": "Overall context is neutral, so the DO range is informational only.",
    }


def _render_weekly_opening_ranges(opening_context: Dict[str, Any]) -> None:
    st.markdown("**Weekly opening ranges**")
    _render_opening_range_chip("Sunday open", opening_context["weekly_sunday"])
    weekly_analysis = opening_context["weekly_monday"]
    active_source = weekly_analysis.get("active_source", "4H")
    _render_opening_range_chip(f"Weekly Open ({active_source})", weekly_analysis)


def _render_opening_range_chip(title: str, analysis: Dict[str, Any]) -> None:
    open_value = analysis.get("open")
    high = analysis.get("high")
    low = analysis.get("low")
    if open_value is None or high is None or low is None:
        st.caption(f"{title}: unavailable")
        return

    text_class = analysis.get("text_class", "")
    st.markdown(
        f"""
        <div class="opening-chip {analysis['css_class']}">
            <div class="opening-chip-title {text_class}">{title}: {_fmt_price(open_value)}</div>
            <div class="opening-chip-detail">Range {_fmt_price(low)} - {_fmt_price(high)} | {analysis['label']} | {analysis['detail']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_trade_filter(trade_filter: Dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class="trade-filter-card {trade_filter['css_class']}">
            <div class="trade-filter-title">{trade_filter['title']}</div>
            <div class="trade-filter-detail">{trade_filter['detail']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_daily_open_status(eurusd: Dict[str, Any], daily_analysis: Dict[str, Any]) -> None:
    current_price = float(eurusd["current_price"])
    daily_open = float(eurusd["daily_open"])
    daily_open_high = eurusd.get("daily_open_high")
    daily_open_low = eurusd.get("daily_open_low")

    if daily_open_high is not None and daily_open_low is not None:
        range_high = max(float(daily_open_high), float(daily_open_low))
        range_low = min(float(daily_open_high), float(daily_open_low))
        if current_price > range_high:
            css_class = "open-above"
            label = f"Above DO range (+{current_price - range_high:.5f})"
        elif current_price < range_low:
            css_class = "open-below"
            label = f"Below DO range ({current_price - range_low:.5f})"
        else:
            css_class = "open-flat"
            label = "Inside DO range"
        range_text = f"Range: {_fmt_price(range_low)} - {_fmt_price(range_high)}"
    else:
        diff = current_price - daily_open
        if diff > 0:
            css_class = "open-above"
            label = f"Above daily open (+{diff:.5f})"
        elif diff < 0:
            css_class = "open-below"
            label = f"Below daily open ({diff:.5f})"
        else:
            css_class = "open-flat"
            label = "At daily open"
        range_text = ""

    window = eurusd.get("daily_open_window", "Daily open")
    text_class = daily_analysis.get("text_class", "")
    raid_text = daily_analysis.get("detail", "")
    st.markdown(
        f"""
        <div class="daily-open-card {css_class}">
            <div class="daily-open-label">Daily open / first NY 4H range</div>
            <div class="daily-open-value {text_class}">{_fmt_price(daily_open)}</div>
            <div class="daily-open-status">{label}</div>
            <div class="daily-open-source">{range_text}</div>
            <div class="daily-open-source">{raid_text}</div>
            <div class="daily-open-source">{window}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_macro_regime(context: Dict[str, Any], score: Dict[str, Any]) -> None:
    st.divider()
    st.subheader("Macro Regime")
    st.caption(f"{score['label']} | Capped macro score: {_fmt_score(score['score'])} | Raw: {_fmt_score(score['raw_score'])}")

    groups = context["macro"]["groups"]
    sections = score["sections"]
    col_rates, col_inflation, col_labor = st.columns(3)
    col_liquidity, col_growth, col_table = st.columns(3)

    with col_rates:
        _render_macro_card("Fed / Rates", sections["rates"], groups.get("rates", {}), ("Fed Funds", "US2Y", "US10Y", "US30Y"))
    with col_inflation:
        _render_macro_card("Inflation", sections["inflation"], groups.get("inflation", {}), ("CPI", "PCE", "Sticky CPI"))
    with col_labor:
        _render_macro_card("Labor Market", sections["labor"], groups.get("labor", {}), ("Payrolls", "Unemployment", "Initial Claims"))
    with col_liquidity:
        _render_macro_card(
            "Liquidity / Dollar",
            sections["liquidity"],
            groups.get("liquidity", {}),
            ("Fed Balance Sheet", "SOFR", "Trade Weighted Dollar"),
        )
    with col_growth:
        _render_macro_card("Growth", sections["growth"], groups.get("growth", {}), ("GDP", "Retail Sales", "Industrial Production"))
    with col_table:
        st.markdown("**Macro Score Contributions**")
        _render_macro_section_scores(sections)

    with st.expander("All FRED macro series"):
        st.dataframe(_macro_rows(groups), hide_index=True, width="stretch")


def _render_macro_card(
    title: str,
    score: Dict[str, Any],
    points: Dict[str, Any],
    labels: tuple,
) -> None:
    _card_header(title, score["score"])
    for label in labels:
        point = points.get(label)
        if not point:
            continue
        st.metric(label, _fmt_macro_value(point), point.get("direction", "flat").title())
    _render_contributions(score["contributions"])


def _render_macro_section_scores(sections: Dict[str, Any]) -> None:
    rows = []
    for label, section in (
        ("Fed / Rates", sections["rates"]),
        ("Inflation", sections["inflation"]),
        ("Labor", sections["labor"]),
        ("Liquidity / Dollar", sections["liquidity"]),
        ("Growth", sections["growth"]),
    ):
        rows.append({"Block": label, "Score": _fmt_score(section['score']), "Raw": _fmt_score(section['raw_score'])})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _macro_rows(groups: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for group_name, points in groups.items():
        for label, point in points.items():
            rows.append(
                {
                    "Group": group_name.title(),
                    "Name": label,
                    "FRED ID": point.get("series_id"),
                    "Latest": _fmt_macro_value(point),
                    "Previous": _fmt_macro_value(point, previous=True),
                    "Direction": str(point.get("direction", "flat")).title(),
                    "Date": point.get("date", ""),
                    "Source": point.get("source", ""),
                }
            )
    return pd.DataFrame(rows)


def _render_events(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.caption("No scheduled EUR/USD calendar events for today.")
        return
    rows = []
    for event in events:
        event_time = event["time_utc"].astimezone(BERLIN_TZ)
        rows.append(
            {
                "Time": event_time.strftime("%H:%M %Z"),
                "Currency": event["currency"],
                "Impact": str(event["impact"]).title(),
                "Event": event.get("title", ""),
                "Forecast": event.get("forecast", ""),
                "Previous": event.get("previous", ""),
            }
        )
    for row in rows:
        meta = f"{row['Time']} | {row['Currency']} | {row['Impact']}"
        details = []
        if row["Forecast"]:
            details.append(f"Forecast: {row['Forecast']}")
        if row["Previous"]:
            details.append(f"Previous: {row['Previous']}")
        suffix = f" ({', '.join(details)})" if details else ""
        st.markdown(f"**{meta}**  \n{row['Event']}{suffix}")


def _render_contributions(contributions: List[Dict[str, Any]]) -> None:
    if not contributions:
        st.caption("No score contribution.")
        return
    for item in contributions:
        value = item["value"]
        st.caption(f"{_fmt_score(value)} {item['name']}: {item['reason']}")


def _render_sources(context: Dict[str, Any]) -> None:
    st.divider()
    st.subheader("Data status")
    rows = [
        {"Dataset": "EUR/USD daily OHLC", "Source": context["eurusd"]["source"]},
        {"Dataset": "EUR/USD daily open", "Source": context["eurusd"].get("daily_open_source", "unknown")},
        {"Dataset": "DXY direction", "Source": context["dxy"]["source"]},
        {"Dataset": "US2Y / US10Y", "Source": context["yields"]["source"]},
        {"Dataset": "Macro regime FRED series", "Source": context["macro"]["source"]},
        {"Dataset": "Euro FX COT", "Source": context["cot"]["source"]},
        {"Dataset": "Economic calendar", "Source": context["calendar"]["source"]},
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(
        "Intraday session levels are placeholder estimates. Calendar events use ForexFactory/FairEconomy XML when available."
    )


def _fmt_score(val: float) -> str:
    """Format scores, supporting both floats and ints cleanly."""
    if val is None:
        return "0"
    if float(val) == int(val):
        return f"{int(val):+d}"
    return f"{val:+.1f}"


def _card_header(title: str, score: float) -> None:
    st.markdown(
        f"""
        <div class="section-card-title">
            <span>{title}</span>
            <strong>{_fmt_score(score)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_price(value: float) -> str:
    return f"{value:.5f}"


def _fmt_macro_value(point: Dict[str, Any], previous: bool = False) -> str:
    value = point.get("previous" if previous else "latest")
    if value is None:
        return "n/a"
    if abs(float(value)) >= 1000000:
        return f"{float(value) / 1000000:.2f}M"
    if abs(float(value)) >= 1000:
        return f"{float(value):,.0f}"
    return f"{float(value):.2f}"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        html {
            -webkit-text-size-adjust: 100%;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }
        h1 {
            line-height: 1.1;
            letter-spacing: 0;
        }
        div[data-testid="stAlert"] {
            margin-bottom: 0.85rem;
        }
        div[data-testid="stMetric"] {
            min-width: 0;
        }
        div[data-testid="stMetric"] label {
            white-space: normal;
            line-height: 1.18;
        }
        div[data-testid="stMetricValue"] {
            overflow-wrap: anywhere;
        }
        div[data-testid="stMetricDelta"] {
            overflow-wrap: anywhere;
        }
        div[data-testid="stDataFrame"] {
            overflow-x: auto;
        }
        .final-bias {
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 8px;
            padding: 18px 20px;
            margin: 12px 0 20px 0;
        }
        .final-bias.bullish { background: rgba(22, 163, 74, 0.10); }
        .final-bias.bearish { background: rgba(220, 38, 38, 0.10); }
        .final-bias.neutral { background: rgba(100, 116, 139, 0.12); }
        .final-label {
            font-size: 1.7rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .final-score {
            margin-top: 4px;
            color: rgba(49, 51, 63, 0.78);
            font-size: 1rem;
            line-height: 1.35;
        }
        .section-card-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            padding: 10px 12px;
            margin: 4px 0 12px 0;
            font-weight: 700;
        }
        .section-card-title strong {
            font-size: 1.15rem;
        }
        .daily-open-card {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 14px;
        }
        .daily-open-card.open-above {
            background: rgba(22, 163, 74, 0.12);
            border-color: rgba(22, 163, 74, 0.38);
        }
        .daily-open-card.open-below {
            background: rgba(220, 38, 38, 0.12);
            border-color: rgba(220, 38, 38, 0.38);
        }
        .daily-open-card.open-flat {
            background: rgba(100, 116, 139, 0.12);
        }
        .daily-open-label {
            font-size: 0.8rem;
            font-weight: 700;
            color: rgba(250, 250, 250, 0.78);
        }
        .daily-open-value {
            font-size: 1.75rem;
            font-weight: 700;
            line-height: 1.2;
            margin-top: 4px;
        }
        .daily-open-value.opening-struck {
            text-decoration: line-through;
            text-decoration-thickness: 2px;
        }
        .daily-open-status {
            font-size: 0.88rem;
            font-weight: 700;
            margin-top: 5px;
        }
        .daily-open-source {
            font-size: 0.74rem;
            color: rgba(250, 250, 250, 0.62);
            margin-top: 4px;
        }
        .trade-filter-card {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            padding: 10px 12px;
            margin: 0 0 14px 0;
        }
        .trade-filter-card.filter-skip {
            background: rgba(234, 179, 8, 0.12);
            border-color: rgba(234, 179, 8, 0.38);
        }
        .trade-filter-card.filter-short {
            background: rgba(220, 38, 38, 0.12);
            border-color: rgba(220, 38, 38, 0.38);
        }
        .trade-filter-card.filter-long {
            background: rgba(22, 163, 74, 0.12);
            border-color: rgba(22, 163, 74, 0.38);
        }
        .trade-filter-card.filter-wait {
            background: rgba(100, 116, 139, 0.12);
        }
        .trade-filter-title {
            font-size: 0.95rem;
            font-weight: 800;
        }
        .trade-filter-detail {
            font-size: 0.8rem;
            color: rgba(250, 250, 250, 0.72);
            margin-top: 4px;
            line-height: 1.35;
        }
        .opening-chip {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            padding: 8px 10px;
            margin: 8px 0;
        }
        .opening-chip.open-above {
            background: rgba(22, 163, 74, 0.10);
            border-color: rgba(22, 163, 74, 0.34);
        }
        .opening-chip.open-below {
            background: rgba(220, 38, 38, 0.10);
            border-color: rgba(220, 38, 38, 0.34);
        }
        .opening-chip.open-flat {
            background: rgba(100, 116, 139, 0.10);
        }
        .opening-chip-title {
            font-weight: 800;
            font-size: 0.86rem;
        }
        .opening-chip-title.opening-struck {
            text-decoration: line-through;
            text-decoration-thickness: 2px;
        }
        .opening-chip-detail {
            color: rgba(250, 250, 250, 0.68);
            font-size: 0.74rem;
            margin-top: 2px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.7rem;
                padding-right: 0.7rem;
                padding-top: 1rem;
            }
            h1 {
                font-size: 1.55rem;
            }
            h2, h3 {
                font-size: 1.15rem;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
            div[data-testid="stMetric"] {
                border-bottom: 1px solid rgba(49, 51, 63, 0.10);
                padding-bottom: 0.45rem;
            }
            div[data-testid="stMetric"]:last-child {
                border-bottom: 0;
            }
            div[data-testid="stMetricValue"] {
                font-size: 1.18rem;
                line-height: 1.12;
            }
            div[data-testid="stMetricDelta"] {
                font-size: 0.8rem;
                line-height: 1.2;
            }
            div[data-testid="stCaptionContainer"] {
                font-size: 0.78rem;
                line-height: 1.32;
            }
            .final-bias {
                padding: 13px 14px;
                margin: 8px 0 14px 0;
            }
            .final-label {
                font-size: 1.28rem;
            }
            .final-score {
                font-size: 0.84rem;
            }
            .section-card-title {
                padding: 9px 10px;
                margin: 2px 0 9px 0;
            }
            .section-card-title strong {
                font-size: 1rem;
            }
            .daily-open-card {
                padding: 10px;
                margin-bottom: 10px;
            }
            .daily-open-value {
                font-size: 1.42rem;
            }
            .trade-filter-card {
                padding: 9px 10px;
                margin-bottom: 10px;
            }
            .opening-chip {
                padding: 8px;
                margin: 7px 0;
            }
            .opening-chip-detail,
            .daily-open-source,
            .trade-filter-detail {
                font-size: 0.74rem;
            }
            .js-plotly-plot,
            .plot-container,
            .svg-container {
                max-width: 100% !important;
            }
        }
        @media (max-width: 420px) {
            .block-container {
                padding-left: 0.45rem;
                padding-right: 0.45rem;
            }
            h1 {
                font-size: 1.35rem;
            }
            .final-label {
                font-size: 1.16rem;
            }
            div[data-testid="stMetricValue"] {
                font-size: 1.08rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
