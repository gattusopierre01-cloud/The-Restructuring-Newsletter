"""Loading and normalising an issue.

An issue lives in issues/<slug>.yaml as structured data, not prose. Every
renderer (PDF, website, email) reads the same object, which is what keeps the
three outputs in step and lets validate.py check an automated draft before a
human ever sees it.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = REPO_ROOT / "issues"
CONFIG_DIR = REPO_ROOT / "config"

# Situations come from anywhere, so the tag is an ISO-style two-letter code
# (DE, NL, BR) plus a few names that are not countries. Case notes are held to
# CASE_JURISDICTIONS, because those are the two systems this publication can
# analyse rather than merely report.
NAMED_JURISDICTIONS = ("EU", "Cross-border")
CASE_JURISDICTIONS = ("UK", "US")
COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


def valid_jurisdiction(value: str) -> bool:
    return bool(COUNTRY_CODE.match(value)) or value in NAMED_JURISDICTIONS


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
class Situation:
    """A restructuring worth knowing about. `stage` groups it in the issue."""

    jurisdiction: str
    name: str
    kind: str
    stage: str = "negotiating"
    venue: str = ""
    debt: str = ""
    parties: str = ""
    notable: str = ""
    source: Source | None = None


@dataclass
class Featured:
    """Situation of the week: one matter explained properly."""

    jurisdiction: str
    name: str
    kind: str
    stage: str = "negotiating"
    venue: str = ""
    debt: str = ""
    parties: str = ""
    paragraphs: list[str] = field(default_factory=list)
    source: Source | None = None

    @property
    def body(self) -> str:
        return " ".join(self.paragraphs)


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
class Concepts:
    """Both sides of the table: the same idea from the two seats."""

    law: Concept
    finance: Concept
    pairing: str = ""

    def pair(self) -> list[tuple[str, Concept]]:
        return [("Law", self.law), ("Finance", self.finance)]


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
    featured: Featured | None = None
    situations: list[Situation] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)
    concepts: Concepts | None = None
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

    def grouped_situations(self, stages: dict[str, str]) -> list[tuple[str, list[Situation]]]:
        """Situations by stage, in the order the config lists them, skipping
        any stage with nothing in it."""
        groups = []
        for key, label in stages.items():
            items = [s for s in self.situations if s.stage == key]
            if items:
                groups.append((label, items))
        return groups

    def word_count(self) -> int:
        chunks: list[str] = list(self.headlines)
        if self.featured:
            chunks.append(self.featured.body)
        for situation in self.situations:
            chunks.append(situation.notable)
        for case in self.cases:
            chunks += [
                case.bottom_line,
                case.facts,
                case.question,
                case.holding,
                case.why_it_matters,
                case.background,
            ]
        if self.concepts:
            chunks += [self.concepts.law.body, self.concepts.finance.body]
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


def _clean_paragraphs(value: Any) -> list[str]:
    """Same, but keeping paragraph breaks.

    In a YAML folded scalar (`>`) a single newline becomes a space and a blank
    line becomes a newline, so the blank lines an author writes survive as
    "\n". The situation of the week is long enough to need paragraphs; every
    other field is a single one.
    """
    if value is None:
        return []
    return [" ".join(part.split()) for part in str(value).split("\n") if part.strip()]


def _as_date(value: Any) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def _parse_concept(raw: Any) -> Concept | None:
    if not raw:
        return None
    return Concept(
        term=_clean(raw.get("term")),
        body=_clean(raw.get("body")),
        see_also=[_clean(x) for x in raw.get("see_also") or []],
    )


def parse_issue(raw: dict[str, Any]) -> Issue:
    concepts_raw = raw.get("concepts") or {}
    law = _parse_concept(concepts_raw.get("law"))
    finance = _parse_concept(concepts_raw.get("finance"))
    concepts = (
        Concepts(law=law, finance=finance, pairing=_clean(concepts_raw.get("pairing")))
        if law and finance
        else None
    )

    featured_raw = raw.get("featured")
    featured = None
    if featured_raw:
        featured = Featured(
            jurisdiction=_clean(featured_raw.get("jurisdiction")),
            name=_clean(featured_raw.get("name")),
            kind=_clean(featured_raw.get("kind")),
            stage=_clean(featured_raw.get("stage")) or "negotiating",
            venue=_clean(featured_raw.get("venue")),
            debt=_clean(featured_raw.get("debt")),
            parties=_clean(featured_raw.get("parties")),
            paragraphs=_clean_paragraphs(featured_raw.get("body")),
            source=Source.parse(featured_raw.get("source")),
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
        featured=featured,
        situations=[
            Situation(
                jurisdiction=_clean(d.get("jurisdiction")),
                name=_clean(d.get("name")),
                kind=_clean(d.get("kind")),
                stage=_clean(d.get("stage")) or "negotiating",
                venue=_clean(d.get("venue")),
                debt=_clean(d.get("debt")),
                parties=_clean(d.get("parties")),
                notable=_clean(d.get("notable")),
                source=Source.parse(d.get("source")),
            )
            for d in raw.get("situations") or []
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
        concepts=concepts,
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
