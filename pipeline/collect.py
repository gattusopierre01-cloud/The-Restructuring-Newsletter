"""Run the enabled collectors and write the week's candidates.

One source failing must not lose the issue, so a collector that errors is
reported and skipped rather than raising. The result lands in
build/candidates.json, which select.py and draft.py read.

    python -m pipeline.collect
    python -m pipeline.collect --days 14
"""

from __future__ import annotations

import argparse
import json

from .model import REPO_ROOT, load_config
from .sources import courtlistener, edgar, findcaselaw, fred, rss
from .sources.base import Candidate, CollectorError

BUILD_DIR = REPO_ROOT / "build"

# source id in config/sources.yaml -> the function that reads it
COLLECTORS = {
    "edgar_bankruptcy_8k": edgar.collect,
    "find_case_law": findcaselaw.collect,
    "courtlistener_opinions": courtlistener.collect,
}

# Feeds are all read by one collector, so they are handled separately rather
# than one entry each.
FEED_KINDS = ("rss", "atom")


def enabled_source_ids(sources: dict) -> list[str]:
    ids: list[str] = []
    for group in ("primary", "commentary"):
        for entry in sources.get(group) or []:
            if entry.get("enabled") and entry["id"] in COLLECTORS:
                ids.append(entry["id"])
    return ids


def any_feeds_enabled(sources: dict) -> bool:
    for group in ("primary", "commentary"):
        for entry in sources.get(group) or []:
            if entry.get("enabled") and entry.get("kind") in FEED_KINDS:
                return True
    return False


def collect_all(days: int) -> tuple[list[Candidate], list[str]]:
    sources = load_config("sources")
    candidates: list[Candidate] = []
    problems: list[str] = []

    for source_id in enabled_source_ids(sources):
        try:
            found = COLLECTORS[source_id](days)
        except CollectorError as exc:
            problems.append(f"{source_id}: {exc}")
            continue
        print(f"  {source_id}: {len(found)} candidates")
        candidates.extend(found)

    if any_feeds_enabled(sources):
        try:
            found = rss.collect(days)
            print(f"  feeds: {len(found)} candidates")
            candidates.extend(found)
        except CollectorError as exc:
            problems.append(f"feeds: {exc}")

    return candidates, problems


def main(argv: list[str] | None = None) -> int:
    sources = load_config("sources")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=sources.get("scoring", {}).get("lookback_days", 10),
        help="how far back to look",
    )
    parser.add_argument(
        "--check-feeds",
        action="store_true",
        help="test every configured feed and report which answer",
    )
    parser.add_argument(
        "--market",
        action="store_true",
        help="also fetch the market backdrop (needs FRED_API_KEY)",
    )
    args = parser.parse_args(argv)

    if args.check_feeds:
        rows = rss.check_feeds()
        for source_id, url, status in rows:
            print(f"{status}\n      {source_id}  {url}")
        failed = sum(1 for _, _, s in rows if s.startswith("FAIL"))
        print(f"\n{len(rows) - failed}/{len(rows)} feeds reachable")
        return 0

    candidates, problems = collect_all(args.days)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_DIR / "candidates.json"
    out.write_text(
        json.dumps([c.as_dict() for c in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n{len(candidates)} candidates → {out.relative_to(REPO_ROOT)}")

    if args.market:
        try:
            indicators = fred.collect()
            market = BUILD_DIR / "market.json"
            market.write_text(
                json.dumps(
                    [
                        {
                            "series_id": i.series_id,
                            "label": i.label,
                            "unit": i.unit,
                            "latest": i.latest,
                            "latest_date": i.latest_date.isoformat() if i.latest_date else None,
                            "previous": i.previous,
                            "change": i.change,
                            "formatted": i.format_value(),
                            "change_text": i.format_change(),
                        }
                        for i in indicators
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"{len(indicators)} indicators → {market.relative_to(REPO_ROOT)}")
            for ind in indicators:
                print(f"  {ind.label:<42} {ind.format_value():>12}   {ind.format_change()}")
        except CollectorError as exc:
            problems.append(f"fred: {exc}")

    for problem in problems:
        print(f"  could not read {problem}")

    # A source being down is worth flagging in the pull request, but it is not
    # a reason to fail the run: the rest of the issue can still be drafted.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
