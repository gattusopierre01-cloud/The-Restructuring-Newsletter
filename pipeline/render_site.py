"""Generate the website pages from the issue files.

MkDocs builds docs/ into a static site. Everything this module writes is
generated, so it is listed in .gitignore: the issue YAML is the source of
truth and the pages are rebuilt on every publish.

    python -m pipeline.render_site
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .model import REPO_ROOT, Issue, load_all_issues, load_config
from .render_pdf import pdf_name

DOCS = REPO_ROOT / "docs"
ISSUE_PAGES = DOCS / "issues"
ASSETS_SRC = REPO_ROOT / "assets"
ASSETS_DEST = DOCS / "assets"

TAG = {"UK": ":flag_gb: UK", "US": ":flag_us: US"}


def tag(jurisdiction: str) -> str:
    return f"`{jurisdiction}`"


def _source_link(source) -> str:
    if source is None:
        return ""
    return f"[{source.title}]({source.url})"


def issue_markdown(issue: Issue, editorial: dict, pdf_href: str) -> str:
    """One issue as a MkDocs page."""
    pub = editorial["publication"]
    out: list[str] = []

    out.append("---")
    out.append(f'title: "Issue {issue.issue} — {issue.period_label}"')
    out.append(f"date: {issue.date_published.isoformat()}")
    out.append("---")
    out.append("")
    out.append(f"# Issue {issue.issue}")
    out.append("")
    out.append(
        f"**{issue.period_label}** · about a {issue.read_minutes()} minute read · "
        f"[Download the PDF]({pdf_href})"
    )
    out.append("")

    if issue.is_specimen:
        out.append('!!! warning "Specimen issue"')
        out.append(f"    {issue.specimen_notice}")
        out.append("")

    # -- headlines ---------------------------------------------------------
    out.append("## The week in three lines")
    out.append("")
    for i, headline in enumerate(issue.headlines, 1):
        out.append(f"{i}. {headline}")
    out.append("")

    # -- situation of the week ---------------------------------------------
    if issue.featured:
        f = issue.featured
        out.append(f"## {editorial['sections']['featured']['label']}")
        out.append("")
        out.append(f"### {tag(f.jurisdiction)} {f.name}")
        out.append("")
        meta = [b for b in (f.kind, f.venue, f.debt, f.parties) if b]
        out.append("*" + " · ".join(meta) + "*")
        out.append("")
        for para in f.paragraphs:
            out.append(para)
            out.append("")
        if f.source:
            out.append(f"→ {_source_link(f.source)}")
            out.append("")

    # -- situations ---------------------------------------------------------
    stages = editorial["sections"]["situations"].get("stages", {})
    groups = issue.grouped_situations(stages)
    if groups:
        out.append(f"## {editorial['sections']['situations']['label']}")
        out.append("")
        for label, items in groups:
            out.append(f"**{label}**")
            out.append("")
            for s_item in items:
                out.append(f"### {tag(s_item.jurisdiction)} {s_item.name}")
                out.append("")
                meta = [b for b in (s_item.kind, s_item.venue, s_item.debt, s_item.parties) if b]
                out.append("*" + " · ".join(meta) + "*")
                out.append("")
                out.append(s_item.notable)
                out.append("")
                if s_item.source:
                    out.append(f"→ {_source_link(s_item.source)}")
                    out.append("")

    # -- case notes --------------------------------------------------------
    if issue.cases:
        out.append("## Case notes")
        out.append("")
        out.append("*United Kingdom and United States only — the two systems this newsletter analyses rather than merely reports.*")
        out.append("")
        for case in issue.cases:
            out.append(f"### {tag(case.jurisdiction)} {case.name}")
            out.append("")
            meta = [b for b in (case.citation, case.court, case.judge) if b]
            if case.date:
                meta.append(f"{case.date:%-d %B %Y}")
            out.append("*" + " · ".join(meta) + "*")
            out.append("")
            out.append(f'!!! abstract "Bottom line"')
            out.append(f"    {case.bottom_line}")
            out.append("")
            for label, text in (
                ("Facts", case.facts),
                ("Question", case.question),
                ("Holding", case.holding),
                ("Why it matters", case.why_it_matters),
            ):
                out.append(f"**{label}.** {text}")
                out.append("")
            out.append('??? info "Background — for readers new to this area"')
            out.append(f"    {case.background}")
            out.append("")
            if case.source:
                out.append(f"→ {_source_link(case.source)}")
                out.append("")

    # -- both sides of the table -------------------------------------------
    if issue.concepts:
        out.append(f"## {editorial['sections']['concepts']['label']}")
        out.append("")
        for side, concept in issue.concepts.pair():
            out.append(f"### {side} — {concept.term}")
            out.append("")
            out.append(concept.body)
            out.append("")
            if concept.see_also:
                out.append("*See also: " + " · ".join(concept.see_also) + "*")
                out.append("")
        if issue.concepts.pairing:
            out.append(f"> {issue.concepts.pairing}")
            out.append("")

    # -- numbers -----------------------------------------------------------
    if issue.numbers:
        out.append("## Numbers")
        out.append("")
        out.append("| Indicator | Latest | Period | Source |")
        out.append("| --- | --- | --- | --- |")
        for n in issue.numbers:
            out.append(
                f"| {n.label} | {n.value} | {n.period} | {_source_link(n.source)} |"
            )
        out.append("")

    # -- watchlist ---------------------------------------------------------
    if issue.watchlist:
        out.append("## Watchlist")
        out.append("")
        for item in issue.watchlist:
            when = f"**{item.date:%-d %b}** · " if item.date else ""
            out.append(f"- {when}{tag(item.jurisdiction)} {item.text}")
        out.append("")

    out.append("---")
    out.append("")
    out.append(f"*{' '.join(editorial['disclaimer'].split())}*")
    out.append("")
    out.append(f"[Download this issue as a PDF]({pdf_href}){{ .md-button }}")
    out.append("")
    return "\n".join(out)


def subscribe_form(editorial: dict) -> str:
    """The signup form. Buttondown handles double opt-in and unsubscribes."""
    email = editorial.get("email", {})
    username = email.get("username", "")
    if email.get("provider") != "buttondown" or not username:
        return "*Email signup is not configured yet — see config/editorial.yaml.*"
    return (
        '<form class="subscribe" action="https://buttondown.email/api/emails/embed-subscribe/'
        f'{username}" method="post" target="popupwindow" '
        f"onsubmit=\"window.open('https://buttondown.email/{username}', 'popupwindow')\">"
        '<label for="bd-email">Email address</label>'
        '<input type="email" name="email" id="bd-email" placeholder="you@firm.com" required>'
        '<input type="submit" value="Subscribe">'
        "</form>"
    )


def index_markdown(issues: list[Issue], editorial: dict) -> str:
    pub = editorial["publication"]
    latest = issues[0]
    out = [
        "---",
        "hide:",
        "  - navigation",
        "---",
        "",
        f"# {pub['name']}",
        "",
        f"*{pub['strapline']}*",
        "",
        " ".join(pub["audience"].split()),
        "",
        "## This week",
        "",
        f"### [Issue {latest.issue} — {latest.period_label}](issues/{latest.slug}.md)",
        "",
    ]
    for headline in latest.headlines:
        out.append(f"- {headline}")
    out += [
        "",
        f"[Read issue {latest.issue}](issues/{latest.slug}.md){{ .md-button .md-button--primary }} "
        f"[Download the PDF](pdf/{pdf_name(latest, editorial)}){{ .md-button }}",
        "",
        "## Get it by email",
        "",
        "One email a week. No tracking beyond what the mail service needs to send it,",
        "and an unsubscribe link in every issue.",
        "",
        subscribe_form(editorial),
        "",
        "## Recent issues",
        "",
    ]
    for issue in issues[:6]:
        out.append(
            f"- **[Issue {issue.issue}](issues/{issue.slug}.md)** — {issue.period_label}"
        )
    out += ["", "[Full archive](archive.md)", ""]
    return "\n".join(out)


def archive_markdown(issues: list[Issue], editorial: dict) -> str:
    out = ["# Archive", "", "Every issue, newest first.", ""]
    out.append("| Issue | Period | Cases | Read | PDF |")
    out.append("| --- | --- | --- | --- | --- |")
    for issue in issues:
        cases = ", ".join(c.name for c in issue.cases) or "—"
        pdf = f"pdf/{pdf_name(issue, editorial)}"
        out.append(
            f"| [{issue.issue}](issues/{issue.slug}.md) | {issue.period_label} | "
            f"{cases} | {issue.read_minutes()} min | [PDF]({pdf}) |"
        )
    out.append("")
    return "\n".join(out)


def glossary_markdown(issues: list[Issue]) -> str:
    """Built from every 'both sides of the table' published so far.

    Split by side rather than merged alphabetically: a reader looking up a
    doctrine and a reader looking up a valuation term are doing different
    things, and after a year there are two useful lists rather than one long
    one.
    """
    out = [
        "# Glossary",
        "",
        "Terms explained in past issues. Each entry links back to the issue it",
        "appeared in. Two lists, because the newsletter explains one legal",
        "concept and one financial one each week.",
        "",
    ]

    sides: dict[str, list[tuple]] = {"Law": [], "Finance": []}
    for issue in issues:
        if not issue.concepts:
            continue
        for side, concept in issue.concepts.pair():
            sides[side].append((concept, issue))

    if not any(sides.values()):
        out.append("*Nothing here yet — the first issue starts this off.*")
        return "\n".join(out) + "\n"

    for side in ("Law", "Finance"):
        out.append(f"## {side}")
        out.append("")
        entries = sorted(sides[side], key=lambda e: e[0].term.lower())
        if not entries:
            out.append("*Nothing here yet.*")
            out.append("")
            continue
        for concept, issue in entries:
            out.append(f"### {concept.term}")
            out.append("")
            out.append(concept.body)
            out.append("")
            out.append(
                f"*From [issue {issue.issue}](issues/{issue.slug}.md), "
                f"{issue.period_label}.*"
            )
            out.append("")
    return "\n".join(out)


def copy_assets() -> list[Path]:
    """The crest lives in assets/ and is shared with the PDF template.
    MkDocs only serves what is under docs/, so it is copied in rather than
    kept in two places where the two could drift apart."""
    if not ASSETS_SRC.is_dir():
        return []
    ASSETS_DEST.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in sorted(ASSETS_SRC.glob("*.svg")):
        dest = ASSETS_DEST / src.name
        shutil.copyfile(src, dest)
        copied.append(dest)
    return copied


def main() -> int:
    editorial = load_config("editorial")
    issues = load_all_issues()
    if not issues:
        print("no issues found in issues/")
        return 1

    # Clear generated issue pages first. Renaming or removing an issue would
    # otherwise leave its page behind, pointing at a PDF that no longer exists,
    # which fails the strict build.
    if ISSUE_PAGES.is_dir():
        for stale in ISSUE_PAGES.glob("*.md"):
            stale.unlink()
    ISSUE_PAGES.mkdir(parents=True, exist_ok=True)
    written: list[Path] = copy_assets()

    for issue in issues:
        pdf_href = f"../pdf/{pdf_name(issue, editorial)}"
        path = ISSUE_PAGES / f"{issue.slug}.md"
        path.write_text(issue_markdown(issue, editorial, pdf_href), encoding="utf-8")
        written.append(path)

    for name, content in (
        ("index.md", index_markdown(issues, editorial)),
        ("archive.md", archive_markdown(issues, editorial)),
        ("glossary.md", glossary_markdown(issues)),
    ):
        path = DOCS / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for path in written:
        print(f"  {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
