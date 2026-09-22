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

    # -- deals -------------------------------------------------------------
    if issue.deals:
        out.append("## Deals and filings")
        out.append("")
        for deal in issue.deals:
            out.append(f"### {tag(deal.jurisdiction)} {deal.name}")
            out.append("")
            meta = [b for b in (deal.kind, deal.venue, deal.debt, deal.parties) if b]
            out.append("*" + " · ".join(meta) + "*")
            out.append("")
            out.append(deal.notable)
            out.append("")
            if deal.source:
                out.append(f"→ {_source_link(deal.source)}")
                out.append("")

    # -- case notes --------------------------------------------------------
    if issue.cases:
        out.append("## Case notes")
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

    # -- concept -----------------------------------------------------------
    if issue.concept:
        out.append("## Concept of the week")
        out.append("")
        out.append(f"### {issue.concept.term}")
        out.append("")
        out.append(issue.concept.body)
        out.append("")
        if issue.concept.see_also:
            out.append("*See also: " + " · ".join(issue.concept.see_also) + "*")
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
    """Built from every 'concept of the week' published so far."""
    out = [
        "# Glossary",
        "",
        "Terms explained in past issues, in alphabetical order. Each entry links",
        "back to the issue it appeared in.",
        "",
    ]
    entries = [(i.concept, i) for i in issues if i.concept]
    if not entries:
        out.append("*Nothing here yet — the first concept of the week starts this off.*")
        return "\n".join(out) + "\n"

    for concept, issue in sorted(entries, key=lambda e: e[0].term.lower()):
        out.append(f"## {concept.term}")
        out.append("")
        out.append(concept.body)
        out.append("")
        out.append(
            f"*From [issue {issue.issue}](issues/{issue.slug}.md), {issue.period_label}.*"
        )
        out.append("")
    return "\n".join(out)


def main() -> int:
    editorial = load_config("editorial")
    issues = load_all_issues()
    if not issues:
        print("no issues found in issues/")
        return 1

    ISSUE_PAGES.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

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
