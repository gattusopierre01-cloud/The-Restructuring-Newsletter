"""Render an issue for email, and send it through Buttondown.

Buttondown takes Markdown, handles double opt-in, unsubscribes and the plain
text alternative, which is what corporate mail filters want. That means this
module only has to produce good Markdown and make one API call.

    python -m pipeline.render_email issues/2026-W39.yaml            # print it
    python -m pipeline.render_email issues/2026-W39.yaml --send      # send it

Sending needs BUTTONDOWN_API_KEY in the environment. A specimen or draft issue
is never sent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .model import Issue, load_config, load_issue
from .render_pdf import pdf_name

API = "https://api.buttondown.email/v1/emails"


def subject(issue: Issue, editorial: dict) -> str:
    return f"{editorial['publication']['name']} — Issue {issue.issue}, {issue.period_label}"


def body_markdown(issue: Issue, editorial: dict) -> str:
    pub = editorial["publication"]
    site = pub["site_url"].rstrip("/")
    issue_url = f"{site}/issues/{issue.slug}/"
    pdf_url = f"{site}/pdf/{pdf_name(issue, editorial)}"
    full = editorial.get("email", {}).get("send_full_issue", True)

    out: list[str] = []
    out.append(f"*{pub['strapline']}*")
    out.append("")
    out.append(
        f"**Issue {issue.issue}** · {issue.period_label} · "
        f"about a {issue.read_minutes()} minute read"
    )
    out.append("")
    out.append("---")
    out.append("")

    out.append("## The week in three lines")
    out.append("")
    for i, headline in enumerate(issue.headlines, 1):
        out.append(f"{i}. {headline}")
    out.append("")

    if not full:
        out.append(f"[Read the full issue]({issue_url}) · [PDF]({pdf_url})")
        out.append("")
        return "\n".join(out) + _footer(editorial, site)

    if issue.featured:
        f = issue.featured
        out.append(f"## {editorial['sections']['featured']['label']}")
        out.append("")
        out.append(f"**{f.jurisdiction} · {f.name}** — {f.kind}")
        out.append("")
        meta = [b for b in (f.venue, f.debt, f.parties) if b]
        if meta:
            out.append("*" + " · ".join(meta) + "*")
            out.append("")
        for para in f.paragraphs:
            out.append(para)
            out.append("")
        if f.source:
            out.append(f"[{f.source.title}]({f.source.url})")
            out.append("")

    stages = editorial["sections"]["situations"].get("stages", {})
    groups = issue.grouped_situations(stages)
    if groups:
        out.append(f"## {editorial['sections']['situations']['label']}")
        out.append("")
        for label, items in groups:
            out.append(f"**{label}**")
            out.append("")
            for item in items:
                out.append(f"**{item.jurisdiction} · {item.name}** — {item.kind}")
                out.append("")
                meta = [b for b in (item.venue, item.debt, item.parties) if b]
                if meta:
                    out.append("*" + " · ".join(meta) + "*")
                    out.append("")
                out.append(item.notable)
                out.append("")
                if item.source:
                    out.append(f"[{item.source.title}]({item.source.url})")
                    out.append("")

    if issue.cases:
        out.append("## Case notes")
        out.append("")
        for case in issue.cases:
            out.append(f"**{case.jurisdiction} · {case.name}**")
            out.append("")
            meta = [b for b in (case.citation, case.court, case.judge) if b]
            out.append("*" + " · ".join(meta) + "*")
            out.append("")
            out.append(f"> **Bottom line.** {case.bottom_line}")
            out.append("")
            for label, text in (
                ("Facts", case.facts),
                ("Question", case.question),
                ("Holding", case.holding),
                ("Why it matters", case.why_it_matters),
                ("Background", case.background),
            ):
                out.append(f"**{label}.** {text}")
                out.append("")
            if case.source:
                out.append(f"[Read the judgment — {case.source.title}]({case.source.url})")
                out.append("")

    if issue.concepts:
        out.append(f"## {editorial['sections']['concepts']['label']}")
        out.append("")
        for side, concept in issue.concepts.pair():
            out.append(f"**{side} — {concept.term}**")
            out.append("")
            out.append(concept.body)
            out.append("")
        if issue.concepts.pairing:
            out.append(f"> {issue.concepts.pairing}")
            out.append("")

    if issue.numbers:
        out.append("## Numbers")
        out.append("")
        for n in issue.numbers:
            line = f"- **{n.label}** — {n.value}"
            if n.period:
                line += f" ({n.period})"
            out.append(line)
        out.append("")

    if issue.watchlist:
        out.append("## Watchlist")
        out.append("")
        for item in issue.watchlist:
            when = f"**{item.date:%-d %b}** · " if item.date else ""
            out.append(f"- {when}{item.jurisdiction} — {item.text}")
        out.append("")

    out.append(f"[Read this issue on the web]({issue_url}) · [Download the PDF]({pdf_url})")
    out.append("")
    return "\n".join(out) + _footer(editorial, site)


def _footer(editorial: dict, site: str) -> str:
    disclaimer = " ".join(editorial["disclaimer"].split())
    return "\n".join(
        [
            "",
            "---",
            "",
            f"*{disclaimer}*",
            "",
            f"[Archive]({site}/archive/) · [Glossary]({site}/glossary/) · "
            f"[About]({site}/about/)",
            "",
        ]
    )


def send(issue: Issue, editorial: dict) -> dict:
    if issue.status != "published":
        raise SystemExit(
            f"refusing to send: status is {issue.status!r}, not 'published'"
        )
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        raise SystemExit("BUTTONDOWN_API_KEY is not set")

    payload = {
        "subject": subject(issue, editorial),
        "body": body_markdown(issue, editorial),
        "status": "about_to_send",
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Buttondown returned {exc.code}: {exc.read().decode('utf-8', 'replace')}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue", type=Path, help="path to an issue YAML file")
    parser.add_argument("--send", action="store_true", help="send it, rather than print it")
    args = parser.parse_args(argv)

    editorial = load_config("editorial")
    issue = load_issue(args.issue)

    if not args.send:
        print(f"Subject: {subject(issue, editorial)}\n")
        print(body_markdown(issue, editorial))
        return 0

    result = send(issue, editorial)
    print(f"sent: {result.get('id', '(no id returned)')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
