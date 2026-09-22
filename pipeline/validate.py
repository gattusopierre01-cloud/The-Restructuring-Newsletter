"""Editorial checks.

This is the safety net under the automation. A draft written by a model can be
fluent and still be wrong in ways that matter here — a case note with no link to
the judgment, a US decision tagged UK, a "concept of the week" that has quietly
grown to 400 words. These checks run in CI, so a bad draft fails the build
rather than reaching a reader.

What it cannot check is whether a summary of a holding is accurate. That is why
a human merges the pull request.

    python -m pipeline.validate                 # every issue
    python -m pipeline.validate issues/2026-W39.yaml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .model import (
    CASE_JURISDICTIONS,
    Issue,
    issue_paths,
    load_config,
    load_issue,
    valid_jurisdiction,
)

# Neutral citation, e.g. [2024] EWCA Civ 24 / [2023] UKSC 5 / [2024] EWHC 12 (Ch)
UK_CITATION = re.compile(r"\[\d{4}\]\s+(UKSC|UKPC|EWCA|EWHC)\b")
# Reporter cite or a docket number, e.g. 603 U.S. 204 (2024) / No. 23-124
US_CITATION = re.compile(r"(\d+\s+[A-Z]\.[A-Za-z0-9.\s]*\s+\d+|No\.\s*\d{1,3}[-–]\d+)")

BANNED_ADJECTIVES = (
    "landmark",
    "seismic",
    "game-changing",
    "game changing",
    "groundbreaking",
    "bombshell",
    "unprecedented",
)


class Report:
    def __init__(self, label: str) -> None:
        self.label = label
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"{'PASS' if self.ok else 'FAIL'}  {self.label}"]
        for msg in self.errors:
            lines.append(f"  error    {msg}")
        for msg in self.warnings:
            lines.append(f"  warning  {msg}")
        return "\n".join(lines)


def _words(text: str) -> int:
    return len(text.split())


def _check_count(rep: Report, rules: dict, label: str, items: list) -> None:
    lo, hi = rules.get("min_items"), rules.get("max_items")
    if lo is not None and len(items) < lo:
        rep.error(f"{label}: {len(items)} items, at least {lo} expected")
    if hi is not None and len(items) > hi:
        rep.error(f"{label}: {len(items)} items, at most {hi} allowed")


def _check_jurisdiction(rep: Report, where: str, value: str, *, cases_only: bool = False) -> None:
    """Situations come from anywhere; case notes may not.

    This is the rule an automated draft is most likely to break — it will
    happily write a note on a German decision because the commentary it found
    was interesting. Reporting a foreign judgment badly is worse than not
    covering it, so the build fails rather than warns.
    """
    if cases_only:
        if value not in CASE_JURISDICTIONS:
            rep.error(
                f"{where}: case notes are {' and '.join(CASE_JURISDICTIONS)} only, "
                f"got {value!r}. A situation from {value!r} belongs in Situations."
            )
        return
    if not valid_jurisdiction(value):
        rep.error(
            f"{where}: {value!r} is not a two-letter country code "
            "(DE, NL, BR) or one of EU, Cross-border"
        )


def _check_source(rep: Report, where: str, source, required: bool) -> None:
    if source is None:
        if required:
            rep.error(f"{where}: no source — every item must link to a primary source")
        return
    if not source.url.startswith("https://"):
        rep.error(f"{where}: source URL is not https ({source.url!r})")


def validate_issue(issue: Issue, editorial: dict) -> Report:
    rep = Report(f"issues/{issue.slug}.yaml  (issue {issue.issue})")
    sections = editorial["sections"]

    # -- dates -------------------------------------------------------------
    if issue.period_end < issue.period_start:
        rep.error("period_end falls before period_start")
    if issue.date_published < issue.period_end:
        rep.error("date_published falls before the end of the period covered")
    if issue.status not in ("specimen", "published", "draft"):
        rep.error(f"status {issue.status!r} is not specimen, draft or published")
    if issue.is_specimen and not issue.specimen_notice:
        rep.error("a specimen issue must carry a specimen_notice")

    # -- headlines ---------------------------------------------------------
    rules = sections["headlines"]
    _check_count(rep, rules, "headlines", issue.headlines)
    for i, line in enumerate(issue.headlines, 1):
        if _words(line) > rules["max_words_per_item"]:
            rep.error(
                f"headline {i}: {_words(line)} words, "
                f"limit {rules['max_words_per_item']}"
            )

    # -- situation of the week ---------------------------------------------
    rules = sections["featured"]
    if issue.featured is None:
        rep.warn("no situation of the week — the section people forward")
    else:
        where = f"featured {issue.featured.name!r}"
        _check_jurisdiction(rep, where, issue.featured.jurisdiction)
        _check_source(rep, where, issue.featured.source, rules.get("require_source", True))
        if _words(issue.featured.body) > rules["max_words"]:
            rep.error(
                f"{where}: {_words(issue.featured.body)} words, "
                f"limit {rules['max_words']}"
            )
        if not issue.featured.body:
            rep.error(f"{where}: no body")

    # -- situations ---------------------------------------------------------
    rules = sections["situations"]
    stages = rules.get("stages", {})
    _check_count(rep, rules, "situations", issue.situations)
    for situation in issue.situations:
        where = f"situation {situation.name!r}"
        _check_jurisdiction(rep, where, situation.jurisdiction)
        _check_source(rep, where, situation.source, rules.get("require_source", True))
        if _words(situation.notable) > rules["max_words_per_item"]:
            rep.error(
                f"{where}: 'notable' is {_words(situation.notable)} words, "
                f"limit {rules['max_words_per_item']}"
            )
        if not situation.kind:
            rep.error(f"{where}: no procedure given (Chapter 11, plan, administration…)")
        if situation.stage not in stages:
            rep.error(
                f"{where}: stage {situation.stage!r} is not one of {list(stages)}"
            )

    names = [s.name for s in issue.situations]
    if issue.featured and issue.featured.name in names:
        rep.warn(
            f"{issue.featured.name!r} appears both as the featured situation "
            "and in the list below it"
        )

    # -- case notes --------------------------------------------------------
    rules = sections["cases"]
    _check_count(rep, rules, "cases", issue.cases)
    for case in issue.cases:
        where = f"case {case.name!r}"
        _check_jurisdiction(rep, where, case.jurisdiction, cases_only=True)
        _check_source(rep, where, case.source, rules.get("require_source", True))

        for field_name, limit in rules["max_words"].items():
            text = getattr(case, field_name, "")
            if not text:
                rep.error(f"{where}: {field_name} is empty")
            elif _words(text) > limit:
                rep.error(
                    f"{where}: {field_name} is {_words(text)} words, limit {limit}"
                )

        if rules.get("require_citation", True):
            if case.jurisdiction == "UK" and not UK_CITATION.search(case.citation):
                rep.error(
                    f"{where}: {case.citation!r} is not a neutral citation "
                    "(expected e.g. [2024] EWCA Civ 24)"
                )
            if case.jurisdiction == "US" and not US_CITATION.search(case.citation):
                rep.error(
                    f"{where}: {case.citation!r} has no reporter cite or docket number"
                )

        if not case.court:
            rep.error(f"{where}: no court given")

    # -- both sides of the table -------------------------------------------
    rules = sections["concepts"]
    if issue.concepts is None:
        rep.warn(
            "no paired concepts — students are half the audience, and the "
            "glossary is built from this section"
        )
    else:
        limit = rules["max_words_each"]
        for side, concept in issue.concepts.pair():
            if not concept.term:
                rep.error(f"concepts: the {side.lower()} side has no term")
            if not concept.body:
                rep.error(f"concepts: {concept.term or side!r} has no body")
            elif _words(concept.body) > limit:
                rep.error(
                    f"concept {concept.term!r} ({side}): "
                    f"{_words(concept.body)} words, limit {limit}"
                )
        if rules.get("pairing_expected", True) and not issue.concepts.pairing:
            rep.warn(
                "concepts: no pairing note — the two sides read better when the "
                "issue says how they connect"
            )

    # -- numbers and watchlist --------------------------------------------
    rules = sections["numbers"]
    _check_count(rep, rules, "numbers", issue.numbers)
    for number in issue.numbers:
        _check_source(
            rep, f"number {number.label!r}", number.source, rules.get("require_source", True)
        )

    rules = sections["watchlist"]
    _check_count(rep, rules, "watchlist", issue.watchlist)
    for item in issue.watchlist:
        _check_jurisdiction(rep, f"watchlist item {item.text[:40]!r}", item.jurisdiction)
        if _words(item.text) > rules["max_words_per_item"]:
            rep.error(
                f"watchlist item {item.text[:40]!r}: {_words(item.text)} words, "
                f"limit {rules['max_words_per_item']}"
            )

    # -- tone and length ---------------------------------------------------
    haystack = " ".join(
        [
            *issue.headlines,
            *(s.notable for s in issue.situations),
            issue.featured.body if issue.featured else "",
            *(c.why_it_matters for c in issue.cases),
            *(c.bottom_line for c in issue.cases),
        ]
    ).lower()
    for word in BANNED_ADJECTIVES:
        if word in haystack:
            rep.warn(f"tone: {word!r} appears — let the facts carry the weight")

    lo, hi = editorial["publication"]["target_read_minutes"]
    minutes = issue.read_minutes()
    if minutes > hi:
        rep.warn(f"length: about a {minutes} minute read, target is {lo}–{hi}")
    elif minutes < lo:
        rep.warn(f"length: about a {minutes} minute read, thin against a {lo}–{hi} target")

    return rep


def main(argv: list[str]) -> int:
    editorial = load_config("editorial")
    paths = [Path(a) for a in argv[1:]] or issue_paths()
    if not paths:
        print("no issues found in issues/")
        return 1

    reports = [validate_issue(load_issue(p), editorial) for p in paths]
    print("\n".join(r.render() for r in reports))

    failed = [r for r in reports if not r.ok]
    print(
        f"\n{len(reports) - len(failed)}/{len(reports)} issues pass"
        + (f", {len(failed)} fail" if failed else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
