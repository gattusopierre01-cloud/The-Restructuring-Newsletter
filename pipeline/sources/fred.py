"""FRED — the market backdrop.

Spreads are a leading indicator of the filings this newsletter reports. When
high-yield spreads widen, the restructurings follow six to eighteen months
later, so a reader who sees the spread moving understands why the situations
section is getting longer. This is the cheapest useful context available: the
ICE BofA indices are on FRED, free, daily, and updated overnight.

Needs a free API key from https://fredaccount.stlouisfed.org/apikeys, set as
FRED_API_KEY.

    python -m pipeline.sources.fred            # this week against last
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import urllib.parse
from dataclasses import dataclass

from ..model import load_config
from .base import CollectorError, fetch_json

API = "https://api.stlouisfed.org/fred/series/observations"


@dataclass
class Indicator:
    series_id: str
    label: str
    unit: str
    latest: float | None
    latest_date: dt.date | None
    previous: float | None
    previous_date: dt.date | None

    @property
    def change(self) -> float | None:
        if self.latest is None or self.previous is None:
            return None
        return self.latest - self.previous

    def format_value(self) -> str:
        if self.latest is None:
            return "n/a"
        if self.unit == "bp":
            return f"{self.latest:,.0f} bp"
        return f"{self.latest:.2f}%"

    def format_change(self) -> str:
        """Week on week, with the sign spelled out — a reader should not have
        to work out whether a minus is tightening or widening."""
        delta = self.change
        if delta is None:
            return ""
        if self.unit == "bp":
            if abs(delta) < 0.5:
                return "unchanged on the week"
            direction = "wider" if delta > 0 else "tighter"
            return f"{abs(delta):,.0f} bp {direction} on the week"
        if abs(delta) < 0.005:
            return "unchanged on the week"
        direction = "up" if delta > 0 else "down"
        return f"{abs(delta):.2f} pts {direction} on the week"


def _observations(series_id: str, start: dt.date, api_key: str) -> list[tuple[dt.date, float]]:
    query = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "observation_start": start.isoformat(),
            "file_type": "json",
            "api_key": api_key,
        }
    )
    payload = fetch_json(f"{API}?{query}")
    rows: list[tuple[dt.date, float]] = []
    for obs in payload.get("observations", []):
        # FRED writes "." for a missing value — a bank holiday, typically.
        if obs.get("value") in (".", "", None):
            continue
        try:
            rows.append((dt.date.fromisoformat(obs["date"]), float(obs["value"])))
        except (ValueError, KeyError):
            continue
    return rows


def collect(*, today: dt.date | None = None, lookback_days: int = 30) -> list[Indicator]:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise CollectorError(
            "FRED_API_KEY is not set — get a free key at "
            "https://fredaccount.stlouisfed.org/apikeys"
        )

    sources = load_config("sources")
    entry = next(
        (s for s in sources.get("market") or [] if s["id"] == "fred" and s.get("enabled")),
        None,
    )
    if entry is None:
        return []

    end = today or dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    indicators: list[Indicator] = []

    for spec in entry.get("series") or []:
        try:
            rows = _observations(spec["id"], start, api_key)
        except CollectorError:
            # One series failing must not lose the rest of the strip.
            indicators.append(
                Indicator(spec["id"], spec["label"], spec.get("unit", ""), None, None, None, None)
            )
            continue

        scale = float(spec.get("scale", 1))
        rows = [(d, v * scale) for d, v in rows]
        if not rows:
            indicators.append(
                Indicator(spec["id"], spec["label"], spec.get("unit", ""), None, None, None, None)
            )
            continue

        latest_date, latest = rows[-1]
        # "A week ago" means the last observation on or before that date, not
        # exactly seven days back: markets are shut at weekends.
        week_ago = latest_date - dt.timedelta(days=7)
        earlier = [(d, v) for d, v in rows if d <= week_ago]
        previous_date, previous = earlier[-1] if earlier else (None, None)

        indicators.append(
            Indicator(
                series_id=spec["id"],
                label=spec["label"],
                unit=spec.get("unit", ""),
                latest=latest,
                latest_date=latest_date,
                previous=previous,
                previous_date=previous_date,
            )
        )
    return indicators


def headline_ids() -> list[str]:
    sources = load_config("sources")
    entry = next((s for s in sources.get("market") or [] if s["id"] == "fred"), None)
    return list(entry.get("headline", [])) if entry else []


def as_numbers_yaml(indicators: list[Indicator]) -> str:
    """The Numbers section of an issue, ready to paste.

    Emitted rather than written straight into the issue file: the numbers are
    mechanical but which of them belongs in a given week is an editorial call.
    """
    wanted = headline_ids()
    chosen = [i for i in indicators if i.series_id in wanted] or indicators
    lines = ["numbers:"]
    for ind in chosen:
        lines.append(f"  - label: {ind.label}")
        lines.append(f"    value: {ind.format_value()}")
        change = ind.format_change()
        lines.append(f"    change: {change}" if change else "    change: null")
        lines.append(f"    period: {'Daily close' if ind.latest_date else 'n/a'}")
        lines.append("    source:")
        lines.append(f"      title: FRED series {ind.series_id}")
        lines.append(f"      url: https://fred.stlouisfed.org/series/{ind.series_id}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yaml", action="store_true", help="print a numbers: block to paste")
    args = parser.parse_args(argv)

    try:
        indicators = collect()
    except CollectorError as exc:
        raise SystemExit(f"fred: {exc}")

    if args.yaml:
        print(as_numbers_yaml(indicators))
        return 0

    for ind in indicators:
        when = f"{ind.latest_date:%-d %b}" if ind.latest_date else "—"
        print(f"  {ind.label:<42} {ind.format_value():>12}   {ind.format_change():<32} {when}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
