"""Economic calendar adapter with ForexFactory/FairEconomy XML fallback."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

import requests

from src.utils.time import BERLIN_TZ, as_utc, utc_now


FOREX_FACTORY_THIS_WEEK_XML = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
RELEVANT_CURRENCIES = ("EUR", "USD")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_CACHE_PATH = PROJECT_ROOT / ".cache" / "ff_calendar_thisweek.xml"


def get_high_impact_events_today(
    now: Optional[datetime] = None,
    currencies: Sequence[str] = RELEVANT_CURRENCIES,
) -> Dict[str, Any]:
    """Return today's relevant economic-calendar events with mock fallback."""
    current = as_utc(now or utc_now())
    wanted = {currency.upper() for currency in currencies}

    try:
        events, source = _load_forex_factory_events()
    except Exception:
        events = _mock_events(current)
        source = "mock"

    today = current.astimezone(BERLIN_TZ).date()
    today_events = [event for event in events if _event_local_date(event) == today]
    relevant_events = [
        event
        for event in today_events
        if event.get("currency") in wanted and event.get("impact", "").lower() != "holiday"
    ]
    relevant_events.sort(key=_event_sort_key)

    other_high_impact = [
        event
        for event in today_events
        if event.get("currency") not in wanted and event.get("impact", "").lower() == "high"
    ]
    other_high_impact.sort(key=_event_sort_key)

    return {
        "source": source,
        "events": relevant_events,
        "other_high_impact_events": other_high_impact,
        "news_within_60m": has_news_within_minutes(relevant_events, current, minutes=60),
    }


def _load_forex_factory_events() -> Tuple[List[Dict[str, Any]], str]:
    try:
        content = _download_forex_factory_xml()
        events = _parse_forex_factory_xml(content)
        _write_calendar_cache(content)
        return events, "forexfactory"
    except Exception:
        if CALENDAR_CACHE_PATH.exists():
            cached_content = CALENDAR_CACHE_PATH.read_bytes()
            events = _parse_forex_factory_xml(cached_content)
            return events, "forexfactory cache"
        raise


def _download_forex_factory_xml() -> bytes:
    response = requests.get(
        FOREX_FACTORY_THIS_WEEK_XML,
        timeout=10,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept": "application/xml,text/xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.content


def _parse_forex_factory_xml(content: bytes) -> List[Dict[str, Any]]:
    root = ElementTree.fromstring(content)
    if root.tag != "weeklyevents":
        raise ValueError("ForexFactory response is not a weekly calendar XML document")

    events = []
    for node in root.findall("event"):
        event = _parse_forex_factory_event(node)
        if event is not None:
            events.append(event)
    if not events:
        raise ValueError("ForexFactory XML returned no usable events")
    return events


def _write_calendar_cache(content: bytes) -> None:
    CALENDAR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_CACHE_PATH.write_bytes(content)


def _parse_forex_factory_event(node: ElementTree.Element) -> Optional[Dict[str, Any]]:
    date_text = _node_text(node, "date")
    time_text = _node_text(node, "time")
    time_utc = _parse_forex_factory_datetime(date_text, time_text)
    if time_utc is None:
        return None

    return {
        "time_utc": time_utc,
        "currency": _node_text(node, "country").upper(),
        "impact": _node_text(node, "impact").lower(),
        "title": _node_text(node, "title"),
        "forecast": _node_text(node, "forecast"),
        "previous": _node_text(node, "previous"),
        "actual": _node_text(node, "actual"),
        "url": _node_text(node, "url"),
    }


def _parse_forex_factory_datetime(date_text: str, time_text: str) -> Optional[datetime]:
    if not date_text or not time_text:
        return None
    normalized_time = time_text.strip().lower()
    if normalized_time in {"all day", "tentative"}:
        return None
    value = datetime.strptime(f"{date_text} {normalized_time}", "%m-%d-%Y %I:%M%p")
    return value.replace(tzinfo=timezone.utc)


def _node_text(node: ElementTree.Element, name: str) -> str:
    child = node.find(name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _mock_events(current: datetime) -> List[Dict[str, Any]]:
    return []


def has_news_within_minutes(events: List[Dict[str, Any]], now: datetime, minutes: int) -> bool:
    """Return whether a high-impact EUR/USD event is scheduled within N minutes."""
    current = as_utc(now)
    window_end = current + timedelta(minutes=minutes)
    for event in events:
        event_time = event.get("time_utc")
        if isinstance(event_time, datetime):
            event_time = as_utc(event_time)
            if current <= event_time <= window_end and event.get("impact") == "high":
                return True
    return False


def _event_local_date(event: Dict[str, Any]) -> Optional[date]:
    event_time = event.get("time_utc")
    if not isinstance(event_time, datetime):
        return None
    return as_utc(event_time).astimezone(BERLIN_TZ).date()


def _event_sort_key(event: Dict[str, Any]) -> datetime:
    event_time = event.get("time_utc")
    if isinstance(event_time, datetime):
        return as_utc(event_time)
    return datetime.max.replace(tzinfo=timezone.utc)
