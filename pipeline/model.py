"""Loading and normalising an issue.

An issue lives in issues/<slug>.yaml as structured data, not prose. Every
renderer (PDF, website, email) reads the same object, which is what keeps the
three outputs in step and lets validate.py check an automated draft before a
human ever sees it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = REPO_ROOT / "issues"
CONFIG_DIR = REPO_ROOT / "config"

JURISDICTIONS = ("UK", "US", "EU", "Cross-border")


def load_config(name: str) -> dict[str, Any]:
    """Read one of the YAML files in config/."""
    with (CONFIG_DIR / f"{name}.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class Source:
    title: str
    url: str

    @classmethod
    def parse(cls, raw: Any) -> "Source | None":
        if not raw:
            return None
        return cls(title=str(raw["title"]).strip(), url=str(raw["url"]).strip())


@dataclass
class Deal:
    jurisdiction: str
    name: str
    kind: str
    venue: str = ""
    debt: str = ""
    parties: str = ""
    notable: str = ""
    source: Source | None = None


@dataclass
class Case:
    jurisdiction: str
    name: str
    citation: str
    court: str
    judge: str = ""
    date: dt.date | None = None
    bottom_line: str = ""
    facts: str = ""
    question: str = ""
    holding: str = ""
    why_it_matters: str = ""
    background: str = ""
    source: Source | None = None


@dataclass
class Concept:
    term: str
    body: str
    see_also: list[str] = field(default_factory=list)


@dataclass
class Number:
    label: str
    value: str
    period: str = ""
    change: str | None = None
    source: Source | None = None


@dataclass
class WatchItem:
    jurisdiction: str
    text: str
    date: dt.date | None = None


@dataclass
class Issue:
    """One edition. `slug` is the ISO year-week, e.g. 2026-W39."""

    issue: int
    slug: str
    status: str
    date_published: dt.date
    period_start: dt.date
    period_end: dt.date
    headlines: list[str] = field(default_factory=list)
    deals: list[Deal] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)
    concept: Concept | None = None
    numbers: list[Number] = field(default_factory=list)
    watchlist: list[WatchItem] = field(default_factory=list)
    specimen_notice: str = ""

    # -- derived -----------------------------------------------------------

    @property
    def is_specimen(self) -> bool:
        return self.status == "specimen"

    @property
    def period_label(self) -> str:
        """'14–20 September 2026', collapsing the month when it repeats."""
        start, end = self.period_start, self.period_end
        if start.month == end.month and start.year == end.year:
            return f"{start.day}–{end.day} {end:%B %Y}"
        if start.year == end.year:
            return f"{start.day} {start:%B} – {end.day} {end:%B %Y}"
        return f"{start.day} {start:%B %Y} – {end.day} {end:%B %Y}"

    @property
    def title(self) -> str:
        return f"Issue {self.issue} — {self.period_label}"

    def word_count(self) -> int:
        chunks: list[str] = list(self.headlines)
        for deal in self.deals:
            chunks.append(deal.notable)
        for case in self.cases:
            chunks += [
                case.bottom_line,
                case.facts,
                case.question,
                case.holding,
                case.why_it_matters,
                case.background,
            ]
        if self.concept:
            chunks.append(self.concept.body)
        chunks += [item.text for item in self.watchlist]
        return sum(len(chunk.split()) for chunk in chunks if chunk)

    def read_minutes(self) -> int:
        """At 225 words a minute, rounded up, floored at 1."""
        return max(1, round(self.word_count() / 225 + 0.5))


def _clean(value: Any) -> str:
    """YAML folded scalars keep a trailing newline; collapse whitespace."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _as_date(value: Any) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def parse_issue(raw: dict[str, Any]) -> Issue:
    concept_raw = raw.get("concept")
    concept = None
    if concept_raw:
        concept = Concept(
            term=_clean(concept_raw.get("term")),
            body=_clean(concept_raw.get("body")),
            see_also=[_clean(x) for x in concept_raw.get("see_also") or []],
        )

    return Issue(
        issue=int(raw["issue"]),
        slug=str(raw["slug"]),
        status=str(raw.get("status", "published")),
        date_published=_as_date(raw["date_published"]),
        period_start=_as_date(raw["period_start"]),
        period_end=_as_date(raw["period_end"]),
        specimen_notice=_clean(raw.get("specimen_notice")),
        headlines=[_clean(h) for h in raw.get("headlines") or []],
        deals=[
            Deal(
                jurisdiction=_clean(d.get("jurisdiction")),
                name=_clean(d.get("name")),
                kind=_clean(d.get("kind")),
                venue=_clean(d.get("venue")),
                debt=_clean(d.get("debt")),
                parties=_clean(d.get("parties")),
                notable=_clean(d.get("notable")),
                source=Source.parse(d.get("source")),
            )
            for d in raw.get("deals") or []
        ],
        cases=[
            Case(
                jurisdiction=_clean(c.get("jurisdiction")),
                name=_clean(c.get("name")),
                citation=_clean(c.get("citation")),
                court=_clean(c.get("court")),
                judge=_clean(c.get("judge")),
                date=_as_date(c.get("date")),
                bottom_line=_clean(c.get("bottom_line")),
                facts=_clean(c.get("facts")),
                question=_clean(c.get("question")),
                holding=_clean(c.get("holding")),
                why_it_matters=_clean(c.get("why_it_matters")),
                background=_clean(c.get("background")),
                source=Source.parse(c.get("source")),
            )
            for c in raw.get("cases") or []
        ],
        concept=concept,
        numbers=[
            Number(
                label=_clean(n.get("label")),
                value=_clean(n.get("value")),
                period=_clean(n.get("period")),
                change=_clean(n.get("change")) or None,
                source=Source.parse(n.get("source")),
            )
            for n in raw.get("numbers") or []
        ],
        watchlist=[
            WatchItem(
                jurisdiction=_clean(w.get("jurisdiction")),
                text=_clean(w.get("text")),
                date=_as_date(w.get("date")),
            )
            for w in raw.get("watchlist") or []
        ],
    )


def load_issue(path: str | Path) -> Issue:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        return parse_issue(yaml.safe_load(fh))


def issue_paths() -> list[Path]:
    """Every issue file, oldest first."""
    return sorted(ISSUES_DIR.glob("*.yaml"))


def load_all_issues() -> list[Issue]:
    """Every issue, newest first — the order the archive shows them in."""
    issues = [load_issue(p) for p in issue_paths()]
    return sorted(issues, key=lambda i: i.date_published, reverse=True)


def latest_issue() -> Issue:
    return load_all_issues()[0]
