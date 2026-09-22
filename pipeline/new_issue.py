"""Start the next issue.

Creates issues/<year>-W<week>.yaml as a skeleton with this week's candidates
pasted in as comments, so the file opens with the raw material already beside
the fields that need filling. Once draft.py is written (phase 4), it will fill
those fields instead of leaving them empty; the skeleton stays the same shape
either way.

    python -m pipeline.new_issue                 # next week's issue
    python -m pipeline.new_issue --week 2026-W40
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .model import ISSUES_DIR, REPO_ROOT, load_all_issues

CANDIDATES = REPO_ROOT / "build" / "candidates.json"

SKELETON = """\
# {slug} — drafted {drafted}
#
# Fill every field, then open a pull request. The build fails if a case note
# has no link to the judgment, if a section runs over its word budget, or if a
# citation is not in the right form: see config/editorial.yaml.
#
# Set status to `published` when it is ready to send.

issue: {number}
slug: {slug}
status: draft

date_published: {published}
period_start: {start}
period_end: {end}

headlines:
  -
  -
  -

featured:                 # Situation of the week — one matter, explained properly
  jurisdiction:           # two-letter code: US, DE, NL, BR… or EU / Cross-border
  name:
  kind:                   # Chapter 11 | Restructuring plan (Part 26A) | StaRUG | WHOA…
  stage: negotiating      # filed | negotiating | completed
  venue:
  debt:
  parties:
  body: >
  source:
    title:
    url:

situations:               # anywhere in the world; thresholds in config/editorial.yaml
  - jurisdiction: US
    name:
    kind:
    stage: filed          # filed | negotiating | completed
    venue:
    debt:
    parties:
    notable: >
    source:
      title:
      url:

cases:
  - jurisdiction: UK        # UK or US only — a matter from elsewhere goes in `situations`
    name:
    citation:               # UK: [2026] EWHC 123 (Ch)   US: No. 26-1234 (S.D. Tex.)
    court:
    judge:
    date:
    bottom_line: >          # two or three lines, for the professional reader
    facts: >
    question: >
    holding: >
    why_it_matters: >
    background: >           # for the student reader: what the doctrine is
    source:
      title:
      url:                  # the judgment itself, not a note about it

concepts:                 # Both sides of the table
  pairing: >              # one line on how the legal test and the number connect
  law:
    term:
    body: >
    see_also: []
  finance:
    term:
    body: >
    see_also: []

numbers: []

watchlist:
  - date:
    jurisdiction: UK
    text: >

# ---------------------------------------------------------------------------
# Candidates found this week. Delete this block before merging.
# ---------------------------------------------------------------------------
{candidates}
"""


def iso_week_slug(day: dt.date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(slug: str) -> tuple[dt.date, dt.date]:
    """Monday to Sunday of the week the slug names."""
    year, week = slug.split("-W")
    monday = dt.date.fromisocalendar(int(year), int(week), 1)
    return monday, monday + dt.timedelta(days=6)


def candidate_comments() -> str:
    if not CANDIDATES.exists():
        return "# (no candidates file — run `python -m pipeline.collect` first)"
    items = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    if not items:
        return "# (no candidates found)"
    lines = []
    for item in items:
        lines.append(f"# [{item['jurisdiction']}] {item['date'] or '—'} {item['title']}")
        if item.get("citation"):
            lines.append(f"#     {item['citation']}")
        lines.append(f"#     {item['url']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", help="ISO week slug, e.g. 2026-W40")
    args = parser.parse_args(argv)

    today = dt.date.today()
    slug = args.week or iso_week_slug(today)
    start, end = week_bounds(slug)

    path = ISSUES_DIR / f"{slug}.yaml"
    if path.exists():
        print(f"{path.relative_to(REPO_ROOT)} already exists — nothing to do")
        return 0

    existing = load_all_issues()
    number = (max((i.issue for i in existing), default=-1)) + 1

    path.write_text(
        SKELETON.format(
            slug=slug,
            number=number,
            drafted=today.isoformat(),
            published=(end + dt.timedelta(days=1)).isoformat(),
            start=start.isoformat(),
            end=end.isoformat(),
            candidates=candidate_comments(),
        ),
        encoding="utf-8",
    )
    print(f"created {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
