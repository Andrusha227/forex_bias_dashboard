"""Streamlit app for the Forex Bias Dashboard."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.data.calendar_data import get_high_impact_events_today
from src.data.cot_data import get_euro_fx_cot
from src.data.fred_data import get_macro_regime_data, get_net_liquidity, get_yield_spread
from src.data.market_data import get_dxy_direction, get_eurusd_snapshot
from src.engine.bias_engine import score_monthly, score_total, score_weekly
from src.engine.macro_engine import score_macro_regime
from src.engine.scoring import CategoryResult
from src.utils.time import BERLIN_TZ


def main() -> None:
    """Render the Streamlit dashboard."""
    load_dotenv()

    st.set_page_config(
        page_title="Forex Bias Dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_styles()

    st.title("Forex Bias Dashboard")
    st.warning("This is a decision-support dashboard, not a trading signal.")

    with st.spinner("Loading market context..."):
        context = _load_context()

    if context is None:
        st.error("No market data sources are available.  Check your API keys and network connection.")
        return

    context = _apply_sidebar_overrides(context)

    # --- Score all categories ---------------------------------------------------
    monthly_cat = score_monthly(context["monthly"])
    weekly_cat = score_weekly(context["weekly"])
    macro_result = score_macro_regime(
        context["macro"],
        yield_spread=context.get("yield_spread"),
        net_liquidity=context.get("net_liquidity"),
    )
    macro_categories: List[CategoryResult] = macro_result["categories"]

    all_categories = [monthly_cat, weekly_cat] + macro_categories
    total = score_total(all_categories)

    # --- Render -----------------------------------------------------------------
    _render_final_bias(total)

    if total.get("partial"):
        unavailable = [
            c["name"]
            for c in total.get("categories", [])
            if c.get("status") == "unavailable"
        ]
        partial = [
            c["name"]
            for c in total.get("categories", [])
            if c.get("status") == "partial"
        ]
        parts = []
        if unavailable:
            parts.append(f"**Unavailable:** {', '.join(unavailable)}")
        if partial:
            parts.append(f"**Partial data:** {', '.join(partial)}")
        st.info(
            "⚠️ Verdict is based on partial data. " + " | ".join(parts) + ". "
            "Missing categories are excluded from the normalized score."
        )

    _render_price_chart(context["eurusd"])

    col_monthly, col_weekly = st.columns(2)
    with col_monthly:
        _render_monthly_card(context, monthly_cat)
    with col_weekly:
        _render_weekly_card(context, weekly_cat)

    _render_macro_regime(context, macro_result, total)
    _render_diagnostics(total)
    _render_calendar(context)
    _render_sources(context)


@st.cache_data(ttl=900, show_spinner=False)
def _load_context() -> Optional[Dict[str, Any]]:
    """Load all data sources.  Returns None if no price data at all."""
    eurusd = get_eurusd_snapshot()
    if eurusd is None:
        return None

    cot = get_euro_fx_cot()          # None when unavailable
    dxy = get_dxy_direction()         # None when unavailable
    macro = get_macro_regime_data()   # always returns dict (groups may be empty)
    calendar = get_high_impact_events_today()  # None when unavailable
    yield_spread = get_yield_spread()  # None when unavailable
    net_liquidity = get_net_liquidity()  # None when unavailable

    monthly = {
        "current_price": eurusd["current_price"],
        "monthly_open": eurusd["monthly_open"],
        "monthly_open_ranges": eurusd.get("monthly_open_ranges"),
        "h4_history": eurusd.get("h4_history"),
        "history": eurusd.get("history"),
        "cot_net_position": cot["net_position"] if cot else None,
        "cot_weekly_change": cot["weekly_change"] if cot else None,
        "cot_metadata": cot,
        "eurusd_metadata": eurusd,
    }
    weekly = {
        "current_price": eurusd["current_price"],
        "weekly_open": eurusd["weekly_open"],
        "weekly_open_ranges": eurusd.get("weekly_open_ranges"),
        "h4_history": eurusd.get("h4_history"),
        "history": eurusd.get("history"),
        "dxy_direction": dxy["direction"] if dxy else None,
        "dxy_metadata": dxy,
        "eurusd_metadata": eurusd,
    }

    return {
        "eurusd": eurusd,
        "cot": cot,
        "dxy": dxy,
        "macro": macro,
        "calendar": calendar,
        "yield_spread": yield_spread,
        "net_liquidity": net_liquidity,
        "monthly": monthly,
        "weekly": weekly,
    }


def _apply_sidebar_overrides(context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply chart-level overrides before scoring."""
    adjusted = copy.deepcopy(context)
    eurusd = adjusted["eurusd"]

    st.sidebar.header("Chart Levels")
    st.sidebar.caption("Override current EUR/USD when your broker feed is more accurate.")

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

    return adjusted


# ---------------------------------------------------------------------------
# Render: verdict
# ---------------------------------------------------------------------------

def _render_final_bias(total: Dict[str, Any]) -> None:
    verdict = total.get("verdict", "Insufficient Data")
    normalized = total.get("normalized_score")

    css_class = _verdict_css(verdict)
    score_text = f"{normalized:+.2f}" if normalized is not None else "n/a"
    avail_w = total.get("available_weight", 0)
    total_w = total.get("total_weight", 0)

    st.markdown(
        f"""
        <div class="final-bias {css_class}">
            <div class="final-label">{verdict}</div>
            <div class="final-score">
                Normalized score: {score_text} &nbsp;|&nbsp; Data coverage: {avail_w:.1f} / {total_w:.1f} weight
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _verdict_css(verdict: str) -> str:
    v = verdict.lower()
    if "strong bullish" in v:
        return "strong-bullish"
    if "bullish" in v:
        return "bullish"
    if "strong bearish" in v:
        return "strong-bearish"
    if "bearish" in v:
        return "bearish"
    return "neutral"


# ---------------------------------------------------------------------------
# Render: price chart
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Render: monthly card
# ---------------------------------------------------------------------------

def _render_monthly_card(context: Dict[str, Any], cat: CategoryResult) -> None:
    eurusd = context["eurusd"]
    cot = context.get("cot")
    current_price = eurusd["current_price"]

    monthly_open_ranges = eurusd.get("monthly_open_ranges")
    candles = eurusd.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = eurusd.get("history")

    from src.engine.opening_engine import analyze_monthly_opening_range
    monthly_analysis = analyze_monthly_opening_range(float(current_price), monthly_open_ranges, candles)

    _card_header("Monthly Structure", cat.score, cat.weight)
    st.metric("Current EUR/USD", _fmt_price(current_price))

    active_source = monthly_analysis.get("active_source", "D")
    _render_opening_range_chip(f"Monthly Open ({active_source})", monthly_analysis)

    if cot is not None:
        st.metric("COT EUR net position", f"{cot['net_position']:,}", f"{cot['weekly_change']:+,} w/w")
    else:
        st.caption("COT data unavailable")

    _render_factor_signals(cat)


# ---------------------------------------------------------------------------
# Render: weekly card
# ---------------------------------------------------------------------------

def _render_weekly_card(context: Dict[str, Any], cat: CategoryResult) -> None:
    eurusd = context["eurusd"]
    dxy = context.get("dxy")

    current_price = eurusd["current_price"]
    weekly_open_ranges = eurusd.get("weekly_open_ranges")
    candles = eurusd.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = eurusd.get("history")

    _card_header("Weekly Structure", cat.score, cat.weight)
    st.metric("Current EUR/USD", _fmt_price(current_price))

    # Weekly Opening Range chip
    if weekly_open_ranges:
        from src.engine.opening_engine import analyze_weekly_opening_range
        weekly_analysis = analyze_weekly_opening_range(float(current_price), weekly_open_ranges, candles)
        active_source = weekly_analysis.get("active_source", "4H")
        _render_opening_range_chip(f"Weekly Open ({active_source})", weekly_analysis)

        # Also show Sunday open if available
        sunday = weekly_open_ranges.get("sunday_open")
        if sunday:
            from src.engine.opening_engine import analyze_monthly_opening_range as _analyze
            # Re-use generic analysis for Sunday
            sunday_range = {
                "d_open": sunday,
                "w_open": sunday,
                "active_source": "Sunday",
                "d_swept_during_first_week": False,
                "is_after_first_week": False,
            }

    st.metric("Previous week high / low",
              f"{_fmt_price(eurusd['previous_week_high'])} / {_fmt_price(eurusd['previous_week_low'])}")

    if dxy is not None:
        st.metric("DXY direction", dxy["direction"].title(),
                  f"{_fmt_price(dxy['latest'])} (5d: {_fmt_price(dxy.get('previous', 0))})" if dxy.get("latest") else "")
    else:
        st.caption("DXY data unavailable")

    _render_factor_signals(cat)


# ---------------------------------------------------------------------------
# Render: macro regime
# ---------------------------------------------------------------------------

def _render_macro_regime(context: Dict[str, Any], macro_result: Dict[str, Any], total: Dict[str, Any]) -> None:
    st.divider()
    st.subheader("Macro Regime")
    macro_label = macro_result.get("label", "Macro Mixed")
    st.caption(f"Regime: {macro_label}")

    macro_cats: List[CategoryResult] = macro_result["categories"]
    groups = context["macro"].get("groups", {})

    # Row 1: Rates, Inflation, Labor
    col_rates, col_inflation, col_labor = st.columns(3)
    with col_rates:
        rates_cat = next((c for c in macro_cats if "Rates" in c.name), None)
        if rates_cat:
            _card_header(rates_cat.name, rates_cat.score, rates_cat.weight)
            _render_macro_points(groups.get("rates", {}), ("Fed Funds", "US2Y", "US10Y", "US30Y"))
            # Yield Spread
            spread = context.get("yield_spread")
            if spread:
                st.metric("Yield Spread (10Y−2Y)",
                          f"{spread['current_spread']:.4f}",
                          spread["direction"].title())
            else:
                st.caption("Yield spread unavailable")
            _render_factor_signals(rates_cat)

    with col_inflation:
        inf_cat = next((c for c in macro_cats if "Inflation" in c.name), None)
        if inf_cat:
            _card_header(inf_cat.name, inf_cat.score, inf_cat.weight)
            _render_macro_points(groups.get("inflation", {}), ("CPI", "PCE", "Sticky CPI"))
            _render_factor_signals(inf_cat)

    with col_labor:
        labor_cat = next((c for c in macro_cats if "Labor" in c.name), None)
        if labor_cat:
            _card_header(labor_cat.name, labor_cat.score, labor_cat.weight)
            _render_macro_points(groups.get("labor", {}), ("Payrolls", "Unemployment", "Initial Claims"))
            _render_factor_signals(labor_cat)

    # Row 2: Liquidity, Growth, Score Summary
    col_liquidity, col_growth, col_table = st.columns(3)
    with col_liquidity:
        liq_cat = next((c for c in macro_cats if "Liquidity" in c.name), None)
        if liq_cat:
            _card_header(liq_cat.name, liq_cat.score, liq_cat.weight)
            # Net Liquidity
            net_liq = context.get("net_liquidity")
            if net_liq:
                st.metric("Net Liquidity (WALCL−TGA−RRP)",
                          _fmt_macro_large(net_liq["current"]),
                          net_liq["direction"].title())
            else:
                st.caption("Net liquidity unavailable")
            _render_macro_points(groups.get("liquidity", {}), ("SOFR",))
            _render_factor_signals(liq_cat)

    with col_growth:
        growth_cat = next((c for c in macro_cats if "Growth" in c.name), None)
        if growth_cat:
            _card_header(growth_cat.name, growth_cat.score, growth_cat.weight)
            _render_macro_points(groups.get("growth", {}), ("GDP", "Retail Sales", "Industrial Production"))
            _render_factor_signals(growth_cat)

    with col_table:
        st.markdown("**Category Score Summary**")
        _render_category_table(total)

    with st.expander("All FRED macro series"):
        st.dataframe(_macro_rows(groups), hide_index=True, use_container_width=True)


def _render_macro_points(points: Dict[str, Any], labels: tuple) -> None:
    for label in labels:
        point = points.get(label)
        if not point:
            st.caption(f"{label}: unavailable")
            continue
        st.metric(label, _fmt_macro_value(point), point.get("direction", "flat").title())


# ---------------------------------------------------------------------------
# Render: calendar (informational, not scored)
# ---------------------------------------------------------------------------

def _render_calendar(context: Dict[str, Any]) -> None:
    calendar = context.get("calendar")
    if calendar is None:
        return

    events = calendar.get("events", [])
    if not events and not calendar.get("other_high_impact_events"):
        return

    st.divider()
    st.subheader("Economic Calendar")
    st.caption(f"Source: {calendar.get('source', 'unknown')} — informational only, not used in scoring.")

    if calendar.get("news_within_60m"):
        st.error("⚠️ High impact EUR/USD news is within the next 60 minutes.")

    _render_events(events)
    if calendar.get("other_high_impact_events"):
        with st.expander("Other high-impact events today"):
            _render_events(calendar["other_high_impact_events"])


# ---------------------------------------------------------------------------
# Render: category table & factor signals
# ---------------------------------------------------------------------------

def _render_category_table(total: Dict[str, Any]) -> None:
    rows = []
    for cat in total.get("categories", []):
        score_str = f"{cat['score']:.2f}" if cat["score"] is not None else "—"
        status_icon = {"ok": "✅", "partial": "⚠️", "unavailable": "❌"}.get(cat["status"], "")
        rows.append({
            "Category": cat["name"],
            "Weight": cat["weight"],
            "Score": score_str,
            "Avail": f"{cat['available_count']}/{cat['total_count']}",
            "Status": status_icon,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_factor_signals(cat: CategoryResult) -> None:
    if not cat.factors:
        st.caption("No factors.")
        return
    for f in cat.factors:
        if f.signal is not None:
            st.caption(f"{_fmt_signal(f.signal)} {f.name}: {f.reason}")
        else:
            st.caption(f"— {f.name}: unavailable")


def _fmt_signal(val: float) -> str:
    if val > 0:
        return f"🟢 +{val:.1f}"
    if val < 0:
        return f"🔴 {val:.1f}"
    return "⚪ 0.0"


# ---------------------------------------------------------------------------
# Render: opening range chip
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Render: events
# ---------------------------------------------------------------------------

def _render_events(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.caption("No scheduled EUR/USD calendar events for today.")
        return
    for event in events:
        event_time = event["time_utc"].astimezone(BERLIN_TZ)
        meta = f"{event_time.strftime('%H:%M %Z')} | {event['currency']} | {str(event['impact']).title()}"
        details = []
        if event.get("forecast"):
            details.append(f"Forecast: {event['forecast']}")
        if event.get("previous"):
            details.append(f"Previous: {event['previous']}")
        suffix = f" ({', '.join(details)})" if details else ""
        st.markdown(f"**{meta}**  \n{event.get('title', '')}{suffix}")


# ---------------------------------------------------------------------------
# Render: data sources
# ---------------------------------------------------------------------------

def _render_sources(context: Dict[str, Any]) -> None:
    st.divider()
    st.subheader("Data Status")
    rows = [
        {"Dataset": "EUR/USD daily OHLC", "Source": context["eurusd"]["source"]},
        {"Dataset": "DXY direction", "Source": context["dxy"]["source"] if context.get("dxy") else "unavailable"},
        {"Dataset": "Macro regime FRED series", "Source": context["macro"]["source"]},
        {"Dataset": "Euro FX COT", "Source": context["cot"]["source"] if context.get("cot") else "unavailable"},
        {"Dataset": "Yield Spread (10Y−2Y)", "Source": context["yield_spread"]["source"] if context.get("yield_spread") else "unavailable"},
        {"Dataset": "Net Liquidity", "Source": context["net_liquidity"]["source"] if context.get("net_liquidity") else "unavailable"},
        {"Dataset": "Economic calendar", "Source": context["calendar"]["source"] if context.get("calendar") else "unavailable"},
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.caption("Calendar events are informational only and do not contribute to the bias score.")


# ---------------------------------------------------------------------------
# Render: diagnostics
# ---------------------------------------------------------------------------

def _render_diagnostics(total: Dict[str, Any]) -> None:
    st.divider()
    st.subheader("Diagnostics & Data Freshness")
    st.caption("Detailed view of mathematical weight renormalization and underlying data points.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Category Contributions & Renormalization**")
        diag_rows = []
        for cat in total.get("categories", []):
            score_str = f"{cat['score']:.2f}" if cat["score"] is not None else "—"
            rw_pct = f"{cat['renormalized_weight'] * 100:.1f}%" if cat["score"] is not None else "0.0%"
            contrib_str = f"{cat['normalized_contribution']:.4f}" if cat["score"] is not None else "—"
            diag_rows.append({
                "Category": cat["name"],
                "Base Weight": cat["weight"],
                "Renormalized Weight": rw_pct,
                "Category Score": score_str,
                "Normalized Contribution": contrib_str,
            })
        st.dataframe(pd.DataFrame(diag_rows), hide_index=True, use_container_width=True)

    with col2:
        st.markdown("**Underlying Factor Details**")
        factor_rows = []
        for cat in total.get("categories", []):
            for f in cat["factors"]:
                sig_str = f"{f['signal']:+.1f}" if f["signal"] is not None else "—"
                freshness_icon = "🟢 Fresh" if f["freshness"] == "fresh" else ("🔴 Stale" if f["freshness"] == "stale" else "⚪ Unknown")
                factor_rows.append({
                    "Category": cat["name"],
                    "Factor": f["name"],
                    "Signal": sig_str,
                    "Timestamp": f["timestamp"],
                    "Source": f["source"],
                    "Freshness": freshness_icon,
                })
        st.dataframe(pd.DataFrame(factor_rows), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_price(value: float) -> str:
    if value is None:
        return "n/a"
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


def _fmt_macro_large(value: float) -> str:
    """Format large numbers (e.g. net liquidity in millions)."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _card_header(title: str, score: Optional[float], weight: float = 0) -> None:
    score_text = f"{score:.2f}" if score is not None else "—"
    weight_text = f"wt {weight:.1f}" if weight else ""
    st.markdown(
        f"""
        <div class="section-card-title">
            <span>{title}</span>
            <strong>{score_text} {weight_text}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _macro_rows(groups: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for group_name, points in groups.items():
        for label, point in points.items():
            if point is None:
                rows.append({
                    "Group": group_name.title(),
                    "Name": label,
                    "FRED ID": "",
                    "Latest": "unavailable",
                    "Previous": "",
                    "Direction": "",
                    "Date": "",
                    "Source": "unavailable",
                })
                continue
            rows.append({
                "Group": group_name.title(),
                "Name": label,
                "FRED ID": point.get("series_id", ""),
                "Latest": _fmt_macro_value(point),
                "Previous": _fmt_macro_value(point, previous=True),
                "Direction": str(point.get("direction", "flat")).title(),
                "Date": point.get("date", ""),
                "Source": point.get("source", ""),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

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
        .final-bias.strong-bullish { background: rgba(22, 163, 74, 0.18); }
        .final-bias.bullish { background: rgba(22, 163, 74, 0.10); }
        .final-bias.bearish { background: rgba(220, 38, 38, 0.10); }
        .final-bias.strong-bearish { background: rgba(220, 38, 38, 0.18); }
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
            .opening-chip {
                padding: 8px;
                margin: 7px 0;
            }
            .opening-chip-detail {
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
