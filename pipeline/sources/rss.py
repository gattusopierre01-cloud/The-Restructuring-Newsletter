"""Generic RSS and Atom collector.

One reader for every feed in config/sources.yaml, rather than a module per
publisher. Feeds move and die without warning, so this also has a health check:

    python -m pipeline.sources.rss --check     # which feeds are alive
    python -m pipeline.sources.rss 10          # what they found in 10 days

Everything read here is commentary unless the entry came from a source marked
`primary` in the config. Commentary finds a development and helps sanity check
a reading of it; it is never the cited authority for what a court held.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from ..model import load_config
from .base import Candidate, CollectorError, fetch

ATOM = "{http://www.w3.org/2005/Atom}"

# What makes an item worth a second look. Broad on purpose — select.py ranks,
# this only filters out the obviously irrelevant.
KEYWORDS = (
    "restructuring", "insolvency", "chapter 11", "chapter 15", "chapter 7",
    "bankruptcy", "administration", "administrator", "liquidation",
    "liquidator", "scheme of arrangement", "part 26a", "cram down",
    "cram-down", "creditor", "debtor", "winding up", "winding-up", "moratorium",
    "distressed", "default", "covenant", "high yield", "high-yield",
    "liability management", "uptier", "dip financing", "wrongful trading",
    "receivership", "examinership", "starug", "whoa", "recuperação",
    "workout", "debt exchange", "recapitalisation", "recapitalization",
)


def _text(el, *names: str) -> str:
    for name in names:
        found = el.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def _entry_date(el) -> dt.date | None:
    raw = _text(el, "pubDate", "published", f"{ATOM}published", f"{ATOM}updated", "updated")
    if not raw:
        return None
    try:  # RFC 822, as RSS uses
        return parsedate_to_datetime(raw).date()
    except (TypeError, ValueError):
        pass
    try:  # ISO 8601, as Atom uses
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _entry_link(el) -> str:
    link = el.find("link")
    if link is not None:
        if link.text and link.text.strip():
            return link.text.strip()
        href = link.get("href")
        if href:
            return href
    atom_link = el.find(f"{ATOM}link")
    if atom_link is not None and atom_link.get("href"):
        return atom_link.get("href")
    return ""


def _strip_html(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())


def parse_feed(raw: bytes, source_id: str, feed_url: str) -> list[Candidate]:
    """Both formats in one pass — an RSS <item> and an Atom <entry> carry the
    same four things we need: title, link, date, summary."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise CollectorError(f"{feed_url} is not valid XML") from exc

    entries = root.iter("item")
    candidates: list[Candidate] = []
    host = urlparse(feed_url).netloc

    for el in list(entries) + list(root.iter(f"{ATOM}entry")):
        title = _text(el, "title", f"{ATOM}title")
        if not title:
            continue
        url = _entry_link(el)
        if not url:
            continue
        summary = _strip_html(
            _text(el, "description", "summary", f"{ATOM}summary", f"{ATOM}content")
        )[:600]

        candidates.append(
            Candidate(
                source_id=source_id,
                kind="signal",
                jurisdiction="",          # commentary rarely says; the drafter decides
                title=_strip_html(title),
                url=url,
                date=_entry_date(el),
                summary=summary,
                extra={"feed": feed_url, "publisher": host},
            )
        )
    return candidates


def relevant(candidate: Candidate) -> bool:
    haystack = f"{candidate.title} {candidate.summary}".lower()
    return any(word in haystack for word in KEYWORDS)


def feed_urls(entry: dict) -> list[str]:
    """A source may carry one `endpoint` or a list of `feeds`."""
    if entry.get("feeds"):
        return list(entry["feeds"])
    if entry.get("endpoint"):
        return [entry["endpoint"]]
    return []


def collect(days: int = 10, *, today: dt.date | None = None) -> list[Candidate]:
    sources = load_config("sources")
    start = (today or dt.date.today()) - dt.timedelta(days=days)

    out: list[Candidate] = []
    seen: set[str] = set()

    for group in ("primary", "commentary"):
        for entry in sources.get(group) or []:
            if not entry.get("enabled") or entry.get("kind") not in ("rss", "atom"):
                continue
            for url in feed_urls(entry):
                try:
                    raw = fetch(url, accept="application/rss+xml, application/atom+xml, application/xml")
                except CollectorError:
                    continue  # a dead feed must not lose the issue
                for candidate in parse_feed(raw, entry["id"], url):
                    if candidate.date and candidate.date < start:
                        continue
                    if not relevant(candidate):
                        continue
                    if candidate.url in seen:
                        continue
                    seen.add(candidate.url)
                    out.append(candidate)
    return out


def check_feeds() -> list[tuple[str, str, str]]:
    """Every configured feed, and whether it actually answers.

    Worth running before trusting the catalogue: feed URLs rot, and a silent
    zero looks exactly like a quiet week.
    """
    sources = load_config("sources")
    results: list[tuple[str, str, str]] = []

    for group in ("primary", "commentary"):
        for entry in sources.get(group) or []:
            if entry.get("kind") not in ("rss", "atom"):
                continue
            state = "on" if entry.get("enabled") else "off"
            for url in feed_urls(entry):
                try:
                    raw = fetch(url, accept="application/rss+xml, application/atom+xml, application/xml")
                except CollectorError as exc:
                    results.append((entry["id"], url, f"FAIL  {exc}"))
                    continue
                try:
                    found = parse_feed(raw, entry["id"], url)
                except CollectorError as exc:
                    results.append((entry["id"], url, f"FAIL  {exc}"))
                    continue
                kept = [c for c in found if relevant(c)]
                results.append(
                    (entry["id"], url, f"OK    {len(found)} entries, {len(kept)} relevant ({state})")
                )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("days", nargs="?", type=int, default=10)
    parser.add_argument("--check", action="store_true", help="test every feed and report")
    args = parser.parse_args(argv)

    if args.check:
        rows = check_feeds()
        if not rows:
            print("no feeds configured")
            return 1
        for source_id, url, status in rows:
            print(f"{status}\n      {source_id}  {url}")
        failed = sum(1 for _, _, s in rows if s.startswith("FAIL"))
        print(f"\n{len(rows) - failed}/{len(rows)} feeds reachable")
        return 0

    found = collect(args.days)
    print(f"{len(found)} relevant items in the last {args.days} days\n")
    for candidate in found:
        print(f"  {candidate.date or '—'}  {candidate.title[:90]}")
        print(f"              {candidate.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
