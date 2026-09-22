"""The National Archives — Find Case Law.

The official source for judgments of the senior courts of England and Wales,
with an Atom feed and no API key. This is what a UK case note is cited to;
a law-firm note about a judgment is never the authority for what it held.

Run on its own to see what it finds:

    python -m pipeline.sources.findcaselaw 10
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from .base import Candidate, CollectorError, fetch, window

FEED = "https://caselaw.nationalarchives.gov.uk/atom.xml"
ATOM = {"atom": "http://www.w3.org/2005/Atom"}

NEUTRAL_CITATION = re.compile(r"\[\d{4}\]\s+(?:UKSC|UKPC|EWCA|EWHC)[^\]]*?(?:\)|\d)")

# Words that make a judgment worth a second look. Kept here rather than in the
# config because they are about parsing, not editorial policy — the editorial
# themes live in config/sources.yaml under scoring.watched_themes.
KEYWORDS = (
    "restructuring plan",
    "part 26a",
    "scheme of arrangement",
    "administration",
    "administrator",
    "liquidation",
    "liquidator",
    "insolvency",
    "wrongful trading",
    "cram down",
    "cram-down",
    "winding up",
    "moratorium",
)


def _court_from_url(url: str) -> str:
    """'…/ewca/civ/2024/24' → 'EWCA Civ'."""
    parts = urllib.parse.urlparse(url).path.strip("/").split("/")
    if len(parts) >= 2:
        return " ".join(p.upper() if len(p) <= 4 else p.title() for p in parts[:2])
    return ""


def collect(days: int = 10, *, today: dt.date | None = None) -> list[Candidate]:
    start, _ = window(days, today=today)
    try:
        root = ET.fromstring(fetch(FEED, accept="application/atom+xml"))
    except ET.ParseError as exc:
        raise CollectorError(f"{FEED} did not return valid Atom") from exc

    candidates: list[Candidate] = []

    for entry in root.findall("atom:entry", ATOM):
        title = (entry.findtext("atom:title", default="", namespaces=ATOM) or "").strip()
        summary = (
            entry.findtext("atom:summary", default="", namespaces=ATOM) or ""
        ).strip()
        link_el = entry.find("atom:link", ATOM)
        url = link_el.get("href", "") if link_el is not None else ""
        updated = entry.findtext("atom:updated", default="", namespaces=ATOM) or ""

        if not url:
            continue

        published: dt.date | None = None
        if updated:
            try:
                published = dt.datetime.fromisoformat(
                    updated.replace("Z", "+00:00")
                ).date()
            except ValueError:
                published = None

        if published and published < start:
            continue

        haystack = f"{title} {summary}".lower()
        if not any(word in haystack for word in KEYWORDS):
            continue

        match = NEUTRAL_CITATION.search(title)
        candidates.append(
            Candidate(
                source_id="find_case_law",
                kind="case",
                jurisdiction="UK",
                title=title,
                url=url,
                date=published,
                court=_court_from_url(url),
                citation=match.group(0) if match else "",
                summary=summary,
            )
        )

    return candidates


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    try:
        found = collect(days)
    except CollectorError as exc:
        raise SystemExit(f"findcaselaw: {exc}")
    print(f"{len(found)} judgments in the last {days} days\n")
    for candidate in found:
        print(f"  {candidate.date}  {candidate.title}")
        print(f"              {candidate.url}")
