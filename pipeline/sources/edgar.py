"""SEC EDGAR — Form 8-K, Item 1.03 (bankruptcy or receivership).

A US public company that files for bankruptcy has to report it on Form 8-K
under Item 1.03. That makes EDGAR full-text search the cleanest free signal
that a listed issuer has filed, and it needs no API key.

Note: full-text search covers roughly the last five years and indexes a filing
a short while after it is submitted, so an 8-K filed late on a Friday may not
appear until the following day. The lookback window in config/sources.yaml
overlaps between issues to cover that.

Run on its own to see what it finds:

    python -m pipeline.sources.edgar 10
"""

from __future__ import annotations

import datetime as dt
import sys
import urllib.parse

from .base import Candidate, CollectorError, fetch_json, window

SEARCH = "https://efts.sec.gov/LATEST/search-index"
FILING_BASE = "https://www.sec.gov/Archives/edgar/data"


def _filing_url(cik: str, accession: str) -> str:
    """Build the human-readable filing index URL from a search hit."""
    cik_plain = str(int(cik))  # EDGAR pads CIKs with zeros; the path does not
    accession_plain = accession.replace("-", "")
    return f"{FILING_BASE}/{cik_plain}/{accession_plain}/{accession}-index.htm"


def collect(days: int = 10, *, today: dt.date | None = None) -> list[Candidate]:
    start, end = window(days, today=today)
    query = urllib.parse.urlencode(
        {
            "q": '"Item 1.03"',
            "forms": "8-K",
            "dateRange": "custom",
            "startdt": start.isoformat(),
            "enddt": end.isoformat(),
        }
    )
    payload = fetch_json(f"{SEARCH}?{query}")

    hits = payload.get("hits", {}).get("hits", [])
    candidates: list[Candidate] = []

    for hit in hits:
        source = hit.get("_source", {})
        names = source.get("display_names") or []
        ciks = source.get("ciks") or []
        if not names or not ciks:
            continue

        # The hit id looks like "0000912057-24-000123:doc.htm".
        accession = str(hit.get("_id", "")).split(":", 1)[0]
        if not accession:
            continue

        filed = source.get("file_date")
        candidates.append(
            Candidate(
                source_id="edgar_bankruptcy_8k",
                kind="filing",
                jurisdiction="US",
                title=names[0],
                url=_filing_url(ciks[0], accession),
                date=dt.date.fromisoformat(filed) if filed else None,
                summary="Form 8-K reporting bankruptcy or receivership (Item 1.03).",
                extra={
                    "cik": ciks[0],
                    "accession": accession,
                    "form": source.get("root_form", "8-K"),
                },
            )
        )

    return candidates


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    try:
        found = collect(days)
    except CollectorError as exc:
        raise SystemExit(f"edgar: {exc}")
    print(f"{len(found)} filings in the last {days} days\n")
    for candidate in found:
        print(f"  {candidate.date}  {candidate.title}")
        print(f"              {candidate.url}")
