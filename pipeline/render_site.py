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


def _source_html(source) -> str:
    """Markdown is not processed inside a plain HTML block, so a source line
    living in a styled <p> has to be written as HTML."""
    if source is None:
        return ""
    return f'<a href="{source.url}">{source.title}</a>' 


def issue_markdown(issue: Issue, editorial: dict, pdf_href: str) -> str:
    """One issue as a MkDocs page.

    Emits explicit wrappers (`rb-featured`, `rb-case`, `rb-bothsides`…) rather
    than bare Markdown, so the stylesheet can give the page the same shape as
    the PDF. `md_in_html` lets Markdown keep working inside them.
    """
    pub = editorial["publication"]
    sections = editorial["sections"]
    out: list[str] = []

    out.append("---")
    out.append(f'title: "Issue {issue.issue} — {issue.period_label}"')
    out.append(f"date: {issue.date_published.isoformat()}")
    out.append("---")
    out.append("")

    # -- masthead, echoing the PDF -----------------------------------------
    out.append('<div class="rb-masthead" markdown>')
    out.append('<img src="../../assets/crest.svg" alt="" class="rb-crest">')
    out.append('<div class="rb-masthead-text" markdown>')
    # The wordmark IS the page heading: hiding a separate h1 confused the
    # theme's scroll behaviour, and the page should have a real heading anyway.
    out.append(f'# {pub["name"]}')
    out.append("")
    out.append(f'<p class="rb-strapline">{pub["strapline"]}</p>')
    out.append("</div>")
    out.append('<div class="rb-issue-meta" markdown>')
    out.append(f"Issue {issue.issue}<br>{issue.period_label}<br>")
    out.append(f"about a {issue.read_minutes()} minute read")
    out.append("</div>")
    out.append("</div>")
    out.append("")
    out.append(f'[Download the PDF]({pdf_href}){{ .md-button .rb-pdf }}')
    out.append("")

    if issue.is_specimen:
        out.append('!!! warning "Specimen issue"')
        out.append(f"    {issue.specimen_notice}")
        out.append("")

    # -- headlines ---------------------------------------------------------
    out.append(f"## {sections['headlines']['label']}")
    out.append("")
    for i, headline in enumerate(issue.headlines, 1):
        out.append(f"{i}. {headline}")
    out.append("")

    # -- situation of the week ---------------------------------------------
    if issue.featured:
        f = issue.featured
        out.append(f"## {sections['featured']['label']}")
        out.append("")
        out.append('<div class="rb-featured" markdown>')
        out.append(f"### {tag(f.jurisdiction)} {f.name}")
        out.append("")
        out.append(f'<p class="rb-kind">{f.kind}</p>')
        meta = [b for b in (f.venue, f.debt, f.parties) if b]
        if meta:
            out.append(f'<p class="rb-meta">{" · ".join(meta)}</p>')
        out.append("")
        for para in f.paragraphs:
            out.append(para)
            out.append("")
        if f.source:
            out.append(f'<p class="rb-source">→ {_source_html(f.source)}</p>')
        out.append("</div>")
        out.append("")

    # -- situations ---------------------------------------------------------
    stages = sections["situations"].get("stages", {})
    groups = issue.grouped_situations(stages)
    if groups:
        out.append(f"## {sections['situations']['label']}")
        out.append("")
        for label, items in groups:
            out.append(f'<p class="rb-stage">{label}</p>')
            out.append("")
            for item in items:
                out.append('<div class="rb-situation" markdown>')
                out.append(f"### {tag(item.jurisdiction)} {item.name}")
                out.append("")
                out.append(f'<p class="rb-kind">{item.kind}</p>')
                meta = [b for b in (item.venue, item.debt, item.parties) if b]
                if meta:
                    out.append(f'<p class="rb-meta">{" · ".join(meta)}</p>')
                out.append("")
                out.append(item.notable)
                out.append("")
                if item.source:
                    out.append(f'<p class="rb-source">→ {_source_html(item.source)}</p>')
                out.append("</div>")
                out.append("")

    # -- case notes ---------------------------------------------------------
    if issue.cases:
        out.append(f"## {sections['cases']['label']}")
        out.append("")
        out.append(
            '<p class="rb-scope">United Kingdom and United States only — the two '
            "systems this newsletter analyses rather than merely reports.</p>"
        )
        out.append("")
        for case in issue.cases:
            out.append('<div class="rb-case" markdown>')
            out.append(f"### {tag(case.jurisdiction)} {case.name}")
            out.append("")
            meta = [b for b in (case.citation, case.court, case.judge) if b]
            if case.date:
                meta.append(f"{case.date:%-d %B %Y}")
            out.append(f'<p class="rb-meta">{" · ".join(meta)}</p>')
            out.append("")
            out.append('<div class="rb-bottomline" markdown>')
            out.append('<p class="rb-label">Bottom line</p>')
            out.append("")
            out.append(case.bottom_line)
            out.append("</div>")
            out.append("")
            for label, text in (
                ("Facts", case.facts),
                ("Question", case.question),
                ("Holding", case.holding),
                ("Why it matters", case.why_it_matters),
            ):
                out.append('<div class="rb-field" markdown>')
                out.append(f'<p class="rb-label">{label}</p>')
                out.append("")
                out.append(text)
                out.append("</div>")
                out.append("")
            out.append('<div class="rb-field rb-background" markdown>')
            out.append('<p class="rb-label">Background — for readers new to this area</p>')
            out.append("")
            out.append(case.background)
            out.append("</div>")
            out.append("")
            if case.source:
                out.append(f'<p class="rb-source">→ {_source_html(case.source)}</p>')
            out.append("</div>")
            out.append("")

    # -- both sides of the table -------------------------------------------
    if issue.concepts:
        out.append(f"## {sections['concepts']['label']}")
        out.append("")
        out.append('<div class="rb-bothsides" markdown>')
        for side, concept in issue.concepts.pair():
            out.append('<div class="rb-side" markdown>')
            out.append(f'<p class="rb-label">{side}</p>')
            out.append("")
            out.append(f"#### {concept.term}")
            out.append("")
            out.append(concept.body)
            out.append("")
            if concept.see_also:
                out.append(
                    f'<p class="rb-seealso">See also: {" · ".join(concept.see_also)}</p>'
                )
            out.append("</div>")
        out.append("</div>")
        out.append("")
        if issue.concepts.pairing:
            out.append(f'<p class="rb-pairing">{issue.concepts.pairing}</p>')
            out.append("")

    # -- conditions ---------------------------------------------------------
    if issue.conditions or issue.numbers:
        out.append(f"## {sections['conditions']['label']}")
        out.append("")
    if issue.conditions:
        out.append(issue.conditions)
        out.append("")
    if issue.numbers:
        out.append('<div class="rb-numbers" markdown>')
        out.append("")
        out.append("| Indicator | Latest | On the week |")
        out.append("| --- | --- | --- |")
        for n in issue.numbers:
            note = []
            if n.source:
                note.append(_source_html(n.source))
            if n.period:
                note.append(n.period)
            aside = (
                f'<br><span class="rb-num-src">{" · ".join(note)}</span>' if note else ""
            )
            out.append(
                f"| {n.label}{aside} | **{n.value}** | {n.change or '—'} |"
            )
        out.append("")
        out.append("</div>")
        out.append("")

    # -- watchlist ----------------------------------------------------------
    if issue.watchlist:
        out.append(f"## {sections['watchlist']['label']}")
        out.append("")
        for item in issue.watchlist:
            when = f"**{item.date:%-d %b}** · " if item.date else ""
            out.append(f"- {when}{tag(item.jurisdiction)} {item.text}")
        out.append("")

    out.append('<div class="rb-colophon" markdown>')
    out.append(" ".join(editorial["disclaimer"].split()))
    out.append("")
    out.append(f"[Download this issue as a PDF]({pdf_href}){{ .md-button }}")
    out.append("</div>")
    out.append("")
    return "\n".join(out)


def subscribe_form(editorial: dict) -> str:
    """The signup form, in the shape Buttondown documents.

    Two details that matter: the hidden `embed` field, without which the
    subscriber is bounced to Buttondown's own page instead of being handled
    inline; and no JavaScript submit, because Buttondown may need to show a
    CAPTCHA and a fetch() call cannot.
    """
    email = editorial.get("email", {})
    username = email.get("username", "")
    if email.get("provider") != "buttondown" or not username:
        return "*Email signup is not configured yet — see config/editorial.yaml.*"
    return (
        '<form class="subscribe embeddable-buttondown-form" method="post" '
        f'action="https://buttondown.com/api/emails/embed-subscribe/{username}">'
        '<label for="bd-email">Email address</label>'
        '<input type="email" name="email" id="bd-email" placeholder="you@firm.com" required>'
        '<input type="hidden" value="1" name="embed">'
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
        '<div class="rb-masthead rb-masthead--home" markdown>',
        '<img src="assets/crest.svg" alt="" class="rb-crest">',
        '<div class="rb-masthead-text" markdown>',
        f'# {pub["name"]}',
        "",
        f'<p class="rb-strapline">{pub["strapline"]}</p>',
        "</div>",
        "</div>",
        "",
        '<p class="rb-audience">' + " ".join(pub["audience"].split()) + "</p>",
        "",
        "## This week",
        "",
        f'<p class="rb-issue-line">Issue {latest.issue} · {latest.period_label} · '
        f"about a {latest.read_minutes()} minute read</p>",
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
        "One email a week, carrying the whole issue. Unsubscribe in one click.",
        "[What you are signing up for](subscribe.md).",
        "",
        subscribe_form(editorial),
        "",
        "## Previously",
        "",
    ]
    # The current issue is above; this is where it goes when it stops being
    # current.
    earlier = issues[1:6]
    if earlier:
        for issue in earlier:
            headline = issue.headlines[0] if issue.headlines else ""
            out.append(
                f"- **[Issue {issue.issue}](issues/{issue.slug}.md)** · "
                f"{issue.period_label}  \n  {headline}"
            )
        out += ["", "[Every issue](archive.md){ .md-button }", ""]
    else:
        out += [
            "This is the first issue. Past issues will collect here, and in the",
            "[archive](archive.md).",
            "",
        ]
    return "\n".join(out)


def archive_markdown(issues: list[Issue], editorial: dict) -> str:
    """Back issues, newest first, grouped by month.

    Each entry shows enough to decide whether to open it — what was covered
    and which decisions were noted — rather than only a date and a number.
    """
    out = [
        "# Archive",
        "",
        "Every issue published so far. The current one is on",
        "[this week](index.md).",
        "",
    ]

    current_month = None
    for issue in issues:
        month = f"{issue.date_published:%B %Y}"
        if month != current_month:
            out.append(f"## {month}")
            out.append("")
            current_month = month

        out.append('<div class="rb-archive-item" markdown>')
        out.append(
            f"### [Issue {issue.issue} — {issue.period_label}](issues/{issue.slug}.md)"
        )
        out.append("")
        marks = []
        if issue.is_specimen:
            marks.append("specimen")
        marks.append(f"{issue.read_minutes()} minute read")
        jurisdictions = sorted(
            {s.jurisdiction for s in issue.situations}
            | ({issue.featured.jurisdiction} if issue.featured else set())
        )
        if jurisdictions:
            marks.append(" ".join(jurisdictions))
        out.append(f'<p class="rb-archive-meta">{" · ".join(marks)}</p>')
        out.append("")

        if issue.featured:
            out.append(f"**{issue.featured.name}** — {issue.featured.kind}")
            out.append("")
        if issue.cases:
            names = ", ".join(c.name for c in issue.cases)
            out.append(f'<p class="rb-archive-cases">Case notes: {names}</p>')
            out.append("")
        if issue.concepts:
            terms = " · ".join(c.term for _, c in issue.concepts.pair())
            out.append(f'<p class="rb-archive-cases">Concepts: {terms}</p>')
            out.append("")

        out.append(
            f'<p class="rb-archive-links">'
            f'<a href="issues/{issue.slug}/">Read</a> · '
            f'<a href="pdf/{pdf_name(issue, editorial)}">PDF</a></p>'
        )
        out.append("</div>")
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


def subscribe_markdown(editorial: dict) -> str:
    """A page to send people to. A form buried on the front page is hard to
    link to from LinkedIn or an email signature."""
    pub = editorial["publication"]
    return "\n".join(
        [
            "# Subscribe",
            "",
            f"*{pub['strapline']}*",
            "",
            "One email a week, on a Monday. It carries the whole issue — the",
            "situation of the week, the case notes, the concepts and the market",
            "backdrop — so you can read it without leaving your inbox. A PDF of",
            "each issue is linked at the top if you would rather have that.",
            "",
            subscribe_form(editorial),
            "",
            "## What you are signing up for",
            "",
            "- **One email a week.** Nothing else. No launches, no offers.",
            "- **Unsubscribe in one click**, from a link in every issue.",
            "- **Your address is used to send you the newsletter and nothing else.**",
            "  It is not sold, shared or passed to anyone.",
            "",
            "You will be asked to confirm by email before anything is sent, which",
            "is both a legal requirement and a good way of making sure the address",
            "is right.",
            "",
            "## Not ready?",
            "",
            "The [archive](archive.md) is open and always will be. So is the",
            "[glossary](glossary.md), which collects every concept explained so",
            "far.",
            "",
        ]
    )


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
        ("subscribe.md", subscribe_markdown(editorial)),
    ):
        path = DOCS / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for path in written:
        print(f"  {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
