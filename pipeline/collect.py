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
from .sources import edgar, findcaselaw
from .sources.base import Candidate, CollectorError

BUILD_DIR = REPO_ROOT / "build"

# source id in config/sources.yaml -> the function that reads it
COLLECTORS = {
    "edgar_bankruptcy_8k": edgar.collect,
    "find_case_law": findcaselaw.collect,
}


def enabled_source_ids(sources: dict) -> list[str]:
    ids: list[str] = []
    for group in ("primary", "signals"):
        for entry in sources.get(group) or []:
            if entry.get("enabled") and entry["id"] in COLLECTORS:
                ids.append(entry["id"])
    return ids


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
    args = parser.parse_args(argv)

    candidates, problems = collect_all(args.days)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_DIR / "candidates.json"
    out.write_text(
        json.dumps([c.as_dict() for c in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n{len(candidates)} candidates → {out.relative_to(REPO_ROOT)}")
    for problem in problems:
        print(f"  could not read {problem}")

    # A source being down is worth flagging in the pull request, but it is not
    # a reason to fail the run: the rest of the issue can still be drafted.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
