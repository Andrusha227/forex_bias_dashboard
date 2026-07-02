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
from src.utils.translations import t, ts, translate_verdict


def main() -> None:
    """Render the Streamlit dashboard."""
    load_dotenv()

    # --- Initialize Page & Language Session State ------------------------------
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    lang = st.session_state.lang

    st.set_page_config(
        page_title=t("title", lang),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_styles()

    # --- Sidebar Language Selector ----------------------------------------------
    selected_lang = st.sidebar.selectbox(
        "Language / Язык",
        ["en", "ru"],
        index=0 if lang == "en" else 1,
        format_func=lambda x: "English" if x == "en" else "Русский",
        key="lang_selector"
    )
    if selected_lang != lang:
        st.session_state.lang = selected_lang
        st.rerun()

    # --- Render Page Views ------------------------------------------------------
    if st.session_state.page == "learn":
        _render_learn_page(lang)
    else:
        _render_dashboard_page(lang)


def _render_dashboard_page(lang: str) -> None:
    """Render the main dashboard page."""
    # Top Row: Title & Navigation Button
    col_title, col_nav = st.columns([3, 1])
    with col_title:
        st.title(t("title", lang))
    with col_nav:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button(t("learn_btn_label", lang), use_container_width=True):
            st.session_state.page = "learn"
            st.rerun()

    with st.spinner("Loading market context..." if lang == "en" else "Загрузка данных рынка..."):
        context = _load_context()

    if context is None:
        st.error("No market data sources are available. Check your API keys and network connection."
                 if lang == "en" else
                 "Источники рыночных данных недоступны. Проверьте API-ключи и сетевое подключение.")
        return

    context = _apply_sidebar_overrides(context, lang)

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

    # --- Render Verdict Box -----------------------------------------------------
    _render_final_bias(total, lang)

    # --- Renormalization / Partial Data Alert -----------------------------------
    if total.get("partial"):
        unavailable = [
            ts(c["name"], lang)
            for c in total.get("categories", [])
            if c.get("status") == "unavailable"
        ]
        partial = [
            ts(c["name"], lang)
            for c in total.get("categories", [])
            if c.get("status") == "partial"
        ]
        parts = []
        if unavailable:
            parts.append(f"**{t('unavailable_categories', lang)}:** {', '.join(unavailable)}")
        if partial:
            parts.append(f"**{t('partial_categories', lang)}:** {', '.join(partial)}")
        st.info(
            t("partial_data_warn", lang) + " " + " | ".join(parts)
        )

    # --- Main Cards Layout ------------------------------------------------------
    _render_price_chart(context["eurusd"], lang)

    col_monthly, col_weekly = st.columns(2)
    with col_monthly:
        _render_monthly_card(context, monthly_cat, lang)
    with col_weekly:
        _render_weekly_card(context, weekly_cat, lang)

    _render_macro_regime(context, macro_result, total, lang)
    _render_diagnostics(total, lang)
    _render_calendar(context, lang)
    _render_sources(context, lang)


def _render_learn_page(lang: str) -> None:
    """Render the educational Learn page."""
    col_title, col_nav = st.columns([3, 1])
    with col_title:
        st.title(t("learn_title", lang))
    with col_nav:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button(t("back_btn_label", lang), use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    st.markdown(t("learn_intro", lang))
    st.divider()

    st.subheader(t("section_what_dashboard", lang))
    st.markdown(t("what_dashboard_text", lang))
    st.divider()

    st.subheader(t("section_what_cot", lang))
    st.markdown(t("what_cot_text", lang))
    st.divider()

    st.subheader(t("section_what_fed", lang))
    st.markdown(t("what_fed_text", lang))
    st.divider()

    st.subheader(t("section_what_liquidity", lang))
    st.markdown(t("what_liquidity_text", lang))
    st.divider()

    st.subheader(t("section_how_counted", lang))
    st.markdown(t("how_counted_text", lang))


@st.cache_data(ttl=900, show_spinner=False)
def _load_context() -> Optional[Dict[str, Any]]:
    """Load all data sources. Returns None if no price data at all."""
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


def _apply_sidebar_overrides(context: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Apply chart-level overrides before scoring."""
    adjusted = copy.deepcopy(context)
    eurusd = adjusted["eurusd"]

    st.sidebar.header(t("chart_levels", lang))
    st.sidebar.caption(t("override_caption", lang))

    override_current = st.sidebar.checkbox(t("override_checkbox", lang), value=False)
    if override_current:
        current_price = st.sidebar.number_input(
            t("current_eurusd", lang),
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

def _render_final_bias(total: Dict[str, Any], lang: str) -> None:
    verdict = total.get("verdict", "Insufficient Data")
    translated_verdict = translate_verdict(verdict, lang)
    normalized = total.get("normalized_score")

    css_class = _verdict_css(verdict)
    score_text = f"{normalized:+.2f}" if normalized is not None else "n/a"
    avail_w = total.get("available_weight", 0)
    total_w = total.get("total_weight", 0)

    st.markdown(
        f"""
        <div class="final-bias {css_class}">
            <div class="final-label">{translated_verdict}</div>
            <div class="final-score">
                {t("normalized_score_lbl", lang)}: {score_text} &nbsp;|&nbsp; {t("data_coverage_lbl", lang)}: {avail_w:.1f} / {total_w:.1f} {t("weight_lbl", lang)}
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

def _render_price_chart(eurusd: Dict[str, Any], lang: str) -> None:
    history = eurusd.get("history")
    if not isinstance(history, pd.DataFrame) or history.empty:
        return

    chart_data = history.tail(60).copy()
    fig = px.line(chart_data, x="date", y="close", title=t("daily_close_title", lang))
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

def _render_monthly_card(context: Dict[str, Any], cat: CategoryResult, lang: str) -> None:
    eurusd = context["eurusd"]
    cot = context.get("cot")
    current_price = eurusd["current_price"]

    monthly_open_ranges = eurusd.get("monthly_open_ranges")
    candles = eurusd.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = eurusd.get("history")

    from src.engine.opening_engine import analyze_monthly_opening_range
    monthly_analysis = analyze_monthly_opening_range(float(current_price), monthly_open_ranges, candles)

    _card_header(t("monthly_structure", lang), cat.score, cat.weight, lang)
    st.metric(t("current_eurusd", lang), _fmt_price(current_price))

    active_source = monthly_analysis.get("active_source", "D")
    chip_title = f"{t('monthly_open', lang)} ({active_source})"
    _render_opening_range_chip(chip_title, monthly_analysis, lang)

    if cot is not None:
        st.metric(t("cot_net", lang), f"{cot['net_position']:,}",
                  f"{cot['weekly_change']:+,} {t('cot_change', lang)}" if lang == "en" else f"{cot['weekly_change']:+,} к/к")
    else:
        st.caption(t("cot_unavailable", lang))

    _render_factor_signals(cat, lang)


# ---------------------------------------------------------------------------
# Render: weekly card
# ---------------------------------------------------------------------------

def _render_weekly_card(context: Dict[str, Any], cat: CategoryResult, lang: str) -> None:
    eurusd = context["eurusd"]
    dxy = context.get("dxy")

    current_price = eurusd["current_price"]
    weekly_open_ranges = eurusd.get("weekly_open_ranges")
    candles = eurusd.get("h4_history")
    if candles is None or (hasattr(candles, "empty") and candles.empty):
        candles = eurusd.get("history")

    _card_header(t("weekly_structure", lang), cat.score, cat.weight, lang)
    st.metric(t("current_eurusd", lang), _fmt_price(current_price))

    # Weekly Opening Range chip
    if weekly_open_ranges:
        from src.engine.opening_engine import analyze_weekly_opening_range
        weekly_analysis = analyze_weekly_opening_range(float(current_price), weekly_open_ranges, candles)
        active_source = weekly_analysis.get("active_source", "4H")
        chip_title = f"{t('weekly_open', lang)} ({active_source})"
        _render_opening_range_chip(chip_title, weekly_analysis, lang)

        # Also show Sunday open if available
        sunday = weekly_open_ranges.get("sunday_open")
        if sunday:
            # Re-use generic analysis for Sunday
            sunday_range = {
                "d_open": sunday,
                "w_open": sunday,
                "active_source": "Sunday",
                "d_swept_during_first_week": False,
                "is_after_first_week": False,
            }

    st.metric(t("prev_week_high_low", lang),
              f"{_fmt_price(eurusd['previous_week_high'])} / {_fmt_price(eurusd['previous_week_low'])}")

    if dxy is not None:
        dxy_dir_trans = ts(dxy["direction"].title(), lang)
        dxy_delta_lbl = f"{_fmt_price(dxy['latest'])} (5d: {_fmt_price(dxy.get('previous', 0))})" if dxy.get("latest") else ""
        st.metric(t("dxy_direction", lang), dxy_dir_trans, dxy_delta_lbl)
    else:
        st.caption(t("dxy_unavailable", lang))

    _render_factor_signals(cat, lang)


# ---------------------------------------------------------------------------
# Render: macro regime
# ---------------------------------------------------------------------------

def _render_macro_regime(context: Dict[str, Any], macro_result: Dict[str, Any], total: Dict[str, Any], lang: str) -> None:
    st.divider()
    st.subheader(t("macro_regime", lang))
    macro_label = macro_result.get("label", "Macro Mixed")
    translated_macro_label = ts(macro_label, lang)
    st.caption(f"{t('regime_lbl', lang)}: {translated_macro_label}")

    macro_cats: List[CategoryResult] = macro_result["categories"]
    groups = context["macro"].get("groups", {})

    # Row 1: Rates, Inflation, Labor
    col_rates, col_inflation, col_labor = st.columns(3)
    with col_rates:
        rates_cat = next((c for c in macro_cats if "Rates" in c.name), None)
        if rates_cat:
            _card_header(t("rates_yield", lang), rates_cat.score, rates_cat.weight, lang)
            _render_macro_points(groups.get("rates", {}), ("Fed Funds", "US2Y", "US10Y", "US30Y"), lang)
            # Yield Spread
            spread = context.get("yield_spread")
            if spread:
                spread_dir_trans = ts(spread["direction"].title(), lang)
                st.metric(t("yield_spread", lang),
                          f"{spread['current_spread']:.4f}",
                          spread_dir_trans)
            else:
                st.caption(t("yield_spread_unavail", lang))
            _render_factor_signals(rates_cat, lang)

    with col_inflation:
        inf_cat = next((c for c in macro_cats if "Inflation" in c.name), None)
        if inf_cat:
            _card_header(t("inflation", lang), inf_cat.score, inf_cat.weight, lang)
            _render_macro_points(groups.get("inflation", {}), ("CPI", "PCE", "Sticky CPI"), lang)
            _render_factor_signals(inf_cat, lang)

    with col_labor:
        labor_cat = next((c for c in macro_cats if "Labor" in c.name), None)
        if labor_cat:
            _card_header(t("labor_market", lang), labor_cat.score, labor_cat.weight, lang)
            _render_macro_points(groups.get("labor", {}), ("Payrolls", "Unemployment", "Initial Claims"), lang)
            _render_factor_signals(labor_cat, lang)

    # Row 2: Liquidity, Growth, Score Summary
    col_liquidity, col_growth, col_table = st.columns(3)
    with col_liquidity:
        liq_cat = next((c for c in macro_cats if "Liquidity" in c.name), None)
        if liq_cat:
            _card_header(t("liquidity", lang), liq_cat.score, liq_cat.weight, lang)
            # Net Liquidity
            net_liq = context.get("net_liquidity")
            if net_liq:
                net_liq_dir_trans = ts(net_liq["direction"].title(), lang)
                st.metric(t("net_liquidity", lang),
                          _fmt_macro_large(net_liq["current"]),
                          net_liq_dir_trans)
            else:
                st.caption(t("net_liquidity_unavail", lang))
            _render_macro_points(groups.get("liquidity", {}), ("SOFR",), lang)
            _render_factor_signals(liq_cat, lang)

    with col_growth:
        growth_cat = next((c for c in macro_cats if "Growth" in c.name), None)
        if growth_cat:
            _card_header(t("growth", lang), growth_cat.score, growth_cat.weight, lang)
            _render_macro_points(groups.get("growth", {}), ("GDP", "Retail Sales", "Industrial Production"), lang)
            _render_factor_signals(growth_cat, lang)

    with col_table:
        st.markdown(f"**{t('category_score_summary', lang)}**")
        _render_category_table(total, lang)

    with st.expander(t("all_fred_series", lang)):
        st.dataframe(_macro_rows(groups, lang), hide_index=True, use_container_width=True)


def _render_macro_points(points: Dict[str, Any], labels: tuple, lang: str) -> None:
    for label in labels:
        point = points.get(label)
        translated_label = ts(label, lang)
        if not point:
            st.caption(f"{translated_label}: {t('cot_unavailable', lang)}")
            continue
        direction_trans = ts(point.get("direction", "flat").title(), lang)
        st.metric(translated_label, _fmt_macro_value(point), direction_trans)


# ---------------------------------------------------------------------------
# Render: calendar (informational, not scored)
# ---------------------------------------------------------------------------

def _render_calendar(context: Dict[str, Any], lang: str) -> None:
    calendar = context.get("calendar")
    if calendar is None:
        return

    events = calendar.get("events", [])
    if not events and not calendar.get("other_high_impact_events"):
        return

    st.divider()
    st.subheader(t("economic_calendar", lang))
    
    source_text = t("economic_calendar_source", lang).format(source=calendar.get('source', 'unknown'))
    st.caption(source_text)

    if calendar.get("news_within_60m"):
        st.error(t("news_warning", lang))

    _render_events(events, lang)
    if calendar.get("other_high_impact_events"):
        with st.expander(t("other_events_today", lang)):
            _render_events(calendar["other_high_impact_events"], lang)


# ---------------------------------------------------------------------------
# Render: category table & factor signals
# ---------------------------------------------------------------------------

def _render_category_table(total: Dict[str, Any], lang: str) -> None:
    rows = []
    for cat in total.get("categories", []):
        score_str = f"{cat['score']:.2f}" if cat["score"] is not None else "—"
        status_icon = {"ok": "✅", "partial": "⚠️", "unavailable": "❌"}.get(cat["status"], "")
        rows.append({
            t("col_category", lang): ts(cat["name"], lang),
            t("col_weight", lang): cat["weight"],
            t("col_score", lang): score_str,
            t("col_avail", lang): f"{cat['available_count']}/{cat['total_count']}",
            t("col_status", lang): status_icon,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_factor_signals(cat: CategoryResult, lang: str) -> None:
    if not cat.factors:
        st.caption(t("no_factors", lang))
        return
    for f in cat.factors:
        translated_name = ts(f.name, lang)
        translated_reason = ts(f.reason, lang)
        if f.signal is not None:
            st.caption(f"{_fmt_signal(f.signal)} {translated_name}: {translated_reason}")
        else:
            st.caption(f"— {translated_name}: {t('cot_unavailable', lang)}")


def _fmt_signal(val: float) -> str:
    if val > 0:
        return f"🟢 +{val:.1f}"
    if val < 0:
        return f"🔴 {val:.1f}"
    return "⚪ 0.0"


# ---------------------------------------------------------------------------
# Render: opening range chip
# ---------------------------------------------------------------------------

def _render_opening_range_chip(title: str, analysis: Dict[str, Any], lang: str) -> None:
    open_value = analysis.get("open")
    high = analysis.get("high")
    low = analysis.get("low")
    if open_value is None or high is None or low is None:
        st.caption(f"{title}: {t('cot_unavailable', lang)}")
        return

    text_class = analysis.get("text_class", "")
    translated_label = ts(analysis['label'], lang)
    translated_detail = ts(analysis['detail'], lang)

    st.markdown(
        f"""
        <div class="opening-chip {analysis['css_class']}">
            <div class="opening-chip-title {text_class}">{title}: {_fmt_price(open_value)}</div>
            <div class="opening-chip-detail">{ts("Range", lang)} {_fmt_price(low)} - {_fmt_price(high)} | {translated_label} | {translated_detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Render: events
# ---------------------------------------------------------------------------

def _render_events(events: List[Dict[str, Any]], lang: str) -> None:
    if not events:
        st.caption("No scheduled EUR/USD calendar events for today." if lang == "en" else "На сегодня нет запланированных важных новостей по EUR/USD.")
        return
    for event in events:
        event_time = event["time_utc"].astimezone(BERLIN_TZ)
        impact_translated = ts(str(event['impact']).title(), lang)
        meta = f"{event_time.strftime('%H:%M %Z')} | {event['currency']} | {impact_translated}"
        details = []
        if event.get("forecast"):
            forecast_lbl = "Forecast" if lang == "en" else "Прогноз"
            details.append(f"{forecast_lbl}: {event['forecast']}")
        if event.get("previous"):
            prev_lbl = "Previous" if lang == "en" else "Предыдущее"
            details.append(f"{prev_lbl}: {event['previous']}")
        suffix = f" ({', '.join(details)})" if details else ""
        
        event_title = event.get('title', '')
        st.markdown(f"**{meta}**  \n{event_title}{suffix}")


# ---------------------------------------------------------------------------
# Render: data sources
# ---------------------------------------------------------------------------

def _render_sources(context: Dict[str, Any], lang: str) -> None:
    st.divider()
    st.subheader(t("data_status", lang))
    
    rows = [
        {t("dataset", lang): ts("EUR/USD daily OHLC", lang), t("source", lang): context["eurusd"]["source"]},
        {t("dataset", lang): ts("DXY direction", lang), t("source", lang): context["dxy"]["source"] if context.get("dxy") else t("cot_unavailable", lang)},
        {t("dataset", lang): ts("Macro regime FRED series", lang), t("source", lang): context["macro"]["source"]},
        {t("dataset", lang): ts("Euro FX COT", lang), t("source", lang): context["cot"]["source"] if context.get("cot") else t("cot_unavailable", lang)},
        {t("dataset", lang): ts("Yield Spread (10Y−2Y)", lang), t("source", lang): context["yield_spread"]["source"] if context.get("yield_spread") else t("cot_unavailable", lang)},
        {t("dataset", lang): ts("Net Liquidity", lang), t("source", lang): context["net_liquidity"]["source"] if context.get("net_liquidity") else t("cot_unavailable", lang)},
        {t("dataset", lang): ts("Economic calendar", lang), t("source", lang): context["calendar"]["source"] if context.get("calendar") else t("cot_unavailable", lang)},
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.caption(t("calendar_info_caption", lang))


# ---------------------------------------------------------------------------
# Render: diagnostics
# ---------------------------------------------------------------------------

def _render_diagnostics(total: Dict[str, Any], lang: str) -> None:
    st.divider()
    st.subheader(t("diagnostics_title", lang))
    st.caption(t("diagnostics_caption", lang))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t('renormalization_title', lang)}**")
        diag_rows = []
        for cat in total.get("categories", []):
            score_str = f"{cat['score']:.2f}" if cat["score"] is not None else "—"
            rw_pct = f"{cat['renormalized_weight'] * 100:.1f}%" if cat["score"] is not None else "0.0%"
            contrib_str = f"{cat['normalized_contribution']:.4f}" if cat["score"] is not None else "—"
            diag_rows.append({
                t("col_category", lang): ts(cat["name"], lang),
                t("col_base_weight", lang): cat["weight"],
                t("col_renorm_weight", lang): rw_pct,
                t("col_cat_score", lang): score_str,
                t("col_norm_contrib", lang): contrib_str,
            })
        st.dataframe(pd.DataFrame(diag_rows), hide_index=True, use_container_width=True)

    with col2:
        st.markdown(f"**{t('factor_details_title', lang)}**")
        factor_rows = []
        for cat in total.get("categories", []):
            for f in cat["factors"]:
                sig_str = f"{f['signal']:+.1f}" if f["signal"] is not None else "—"
                
                fresh_val = f["freshness"]
                freshness_icon = t("fresh_val", lang) if fresh_val == "fresh" else (t("stale_val", lang) if fresh_val == "stale" else t("unknown_val", lang))
                
                factor_rows.append({
                    t("col_category", lang): ts(cat["name"], lang),
                    t("col_factor", lang): ts(f["name"], lang),
                    t("col_signal", lang): sig_str,
                    t("col_timestamp", lang): f["timestamp"],
                    t("source", lang): f["source"],
                    t("col_freshness", lang): freshness_icon,
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


def _macro_rows(groups: Dict[str, Dict[str, Any]], lang: str) -> pd.DataFrame:
    rows = []
    for group_name, points in groups.items():
        for label, point in points.items():
            translated_group = ts(group_name.title(), lang)
            translated_label = ts(label, lang)
            if point is None:
                rows.append({
                    t("col_category", lang): translated_group,
                    t("col_factor", lang): translated_label,
                    "FRED ID": "",
                    t("col_score", lang) if lang == "en" else "Последнее": t("cot_unavailable", lang),
                    "Previous": "",
                    "Direction": "",
                    "Date": "",
                    "Source": t("cot_unavailable", lang),
                })
                continue
            rows.append({
                t("col_category", lang): translated_group,
                t("col_factor", lang): translated_label,
                "FRED ID": point.get("series_id", ""),
                t("col_score", lang) if lang == "en" else "Последнее": _fmt_macro_value(point),
                "Previous": _fmt_macro_value(point, previous=True),
                "Direction": ts(str(point.get("direction", "flat")).title(), lang),
                "Date": point.get("date", ""),
                "Source": point.get("source", ""),
            })
    return pd.DataFrame(rows)


def _card_header(title: str, score: Optional[float], weight: float = 0, lang: str = "en") -> None:
    score_text = f"{score:.2f}" if score is not None else "—"
    weight_text = f"{t('weight_lbl', lang)} {weight:.1f}" if weight else ""
    st.markdown(
        f"""
        <div class="section-card-title">
            <span>{title}</span>
            <strong>{score_text} {weight_text}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
