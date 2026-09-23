"""CourtListener — US opinions and dockets.

This closes the gap found writing issue 1: the airBaltic filing could not be
linked to the docket itself, so the entry cited commentary instead. That is
below the standard set in config/editorial.yaml.

CourtListener blocks automated page fetching in robots.txt, which is why a
scraper would be both rude and unreliable. The REST API is the documented way
in and is what this uses. A free token lifts the rate limit considerably; set
COURTLISTENER_TOKEN.

    python -m pipeline.sources.courtlistener 10
    python -m pipeline.sources.courtlistener --docket "Air Baltic"
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import urllib.parse

from ..model import load_config
from .base import USER_AGENT, Candidate, CollectorError, fetch_json, window

SEARCH = "https://www.courtlistener.com/api/rest/v4/search/"

# Restructuring vocabulary, as a US court would use it.
QUERY = (
    '"chapter 11" OR "chapter 15" OR "plan of reorganization" OR '
    '"third-party release" OR "cramdown" OR "cram down" OR "absolute priority" '
    'OR "debtor in possession" OR "automatic stay" OR "fraudulent transfer"'
)


def _headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = os.environ.get("COURTLISTENER_TOKEN")
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers


def _get(url: str) -> dict:
    # base.fetch_json does not take custom headers, so the request is built
    # here to carry the token.
    import json
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise CollectorError(
                "CourtListener rate limit hit — set COURTLISTENER_TOKEN for a "
                "higher allowance (free at courtlistener.com)"
            ) from exc
        raise CollectorError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise CollectorError(f"{url} could not be reached: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise CollectorError(f"{url} did not return JSON") from exc


def _courts() -> str:
    sources = load_config("sources")
    entry = next(
        (s for s in sources.get("primary") or [] if s["id"] == "courtlistener_opinions"),
        None,
    )
    return " ".join(entry.get("courts", [])) if entry else ""


def collect(days: int = 10, *, today: dt.date | None = None) -> list[Candidate]:
    """Opinions in the window that use restructuring vocabulary."""
    start, end = window(days, today=today)
    params = {
        "q": QUERY,
        "type": "o",                      # opinions
        "order_by": "dateFiled desc",
        "filed_after": start.strftime("%m/%d/%Y"),
        "filed_before": end.strftime("%m/%d/%Y"),
    }
    courts = _courts()
    if courts:
        params["court"] = courts

    payload = _get(f"{SEARCH}?{urllib.parse.urlencode(params)}")
    candidates: list[Candidate] = []

    for hit in payload.get("results", []):
        absolute = hit.get("absolute_url") or ""
        url = f"https://www.courtlistener.com{absolute}" if absolute.startswith("/") else absolute
        if not url:
            continue
        filed = hit.get("dateFiled")
        try:
            filed_date = dt.date.fromisoformat(filed) if filed else None
        except ValueError:
            filed_date = None

        candidates.append(
            Candidate(
                source_id="courtlistener_opinions",
                kind="case",
                jurisdiction="US",
                title=hit.get("caseName", "").strip(),
                url=url,
                date=filed_date,
                court=hit.get("court", ""),
                citation=", ".join(hit.get("citation", []) or []),
                summary=(hit.get("snippet") or "").strip()[:600],
                extra={"docket_number": hit.get("docketNumber", "")},
            )
        )
    return candidates


def find_docket(name: str) -> list[Candidate]:
    """Look up a named matter's docket — what issue 1 needed for airBaltic.

    Coverage depends on what RECAP holds, so treat a miss as "not in RECAP",
    not as "does not exist".
    """
    params = {"q": f'caseName:("{name}")', "type": "r", "order_by": "dateFiled desc"}
    payload = _get(f"{SEARCH}?{urllib.parse.urlencode(params)}")

    out: list[Candidate] = []
    for hit in payload.get("results", []):
        absolute = hit.get("docket_absolute_url") or hit.get("absolute_url") or ""
        url = f"https://www.courtlistener.com{absolute}" if absolute.startswith("/") else absolute
        if not url:
            continue
        filed = hit.get("dateFiled")
        try:
            filed_date = dt.date.fromisoformat(filed) if filed else None
        except (ValueError, TypeError):
            filed_date = None
        out.append(
            Candidate(
                source_id="courtlistener_dockets",
                kind="filing",
                jurisdiction="US",
                title=hit.get("caseName", "").strip(),
                url=url,
                date=filed_date,
                court=hit.get("court", ""),
                summary=f"Docket {hit.get('docketNumber', '')}".strip(),
                extra={"docket_number": hit.get("docketNumber", "")},
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("days", nargs="?", type=int, default=10)
    parser.add_argument("--docket", help="look up a named matter's docket")
    args = parser.parse_args(argv)

    try:
        found = find_docket(args.docket) if args.docket else collect(args.days)
    except CollectorError as exc:
        raise SystemExit(f"courtlistener: {exc}")

    print(f"{len(found)} results\n")
    for candidate in found:
        print(f"  {candidate.date or '—'}  [{candidate.court}] {candidate.title[:80]}")
        print(f"              {candidate.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
