"""Render an issue to PDF.

The issue is flattened to build/issue.json and Typst does the typesetting.
Keeping presentation in templates/issue.typ and data here means the layout can
be changed without touching Python, and the same JSON could feed a second
template later (a print edition, say) without a second pipeline.

    python -m pipeline.render_pdf                    # every issue
    python -m pipeline.render_pdf issues/2026-W39.yaml
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .model import REPO_ROOT, Issue, issue_paths, load_config, load_issue

BUILD_DIR = REPO_ROOT / "build"
TEMPLATE = REPO_ROOT / "templates" / "issue.typ"
OUTPUT_DIR = REPO_ROOT / "docs" / "pdf"


def _source(src) -> dict | None:
    return None if src is None else asdict(src)


def _situation_meta(item) -> str:
    """The reference line under a situation heading."""
    bits = [b for b in (item.venue, item.debt, item.parties) if b]
    return "  ·  ".join(bits)


def _case_meta(case) -> str:
    bits = [b for b in (case.citation, case.court, case.judge) if b]
    if case.date:
        bits.append(f"{case.date:%-d %B %Y}")
    return "  ·  ".join(bits)


def issue_to_dict(issue: Issue, editorial: dict) -> dict:
    pub = editorial["publication"]
    return {
        "publication": pub["name"],
        "labels": {
            key: editorial["sections"][key]["label"]
            for key in ("headlines", "featured", "situations", "cases",
                        "concepts", "numbers", "watchlist")
        },
        "strapline": pub["strapline"],
        "site_url": pub["site_url"],
        "site_url_label": pub["site_url_label"],
        "disclaimer": " ".join(editorial["disclaimer"].split()),
        "doc_title": f"{pub['name']} — {issue.title}",
        "issue": issue.issue,
        "slug": issue.slug,
        "status": issue.status,
        "specimen_notice": issue.specimen_notice,
        "period_label": issue.period_label,
        "date_published": f"{issue.date_published:%-d %B %Y}",
        "read_minutes": issue.read_minutes(),
        "headlines": issue.headlines,
        "featured": (
            None
            if issue.featured is None
            else {
                "jurisdiction": issue.featured.jurisdiction,
                "name": issue.featured.name,
                "kind": issue.featured.kind,
                "meta_line": _situation_meta(issue.featured),
                "body": issue.featured.body,
                "source": _source(issue.featured.source),
            }
        ),
        # Grouped here rather than in the template: Typst should lay out, not
        # decide what belongs together.
        "situation_groups": [
            {
                "label": label,
                "items": [
                    {
                        "jurisdiction": s.jurisdiction,
                        "name": s.name,
                        "kind": s.kind,
                        "meta_line": _situation_meta(s),
                        "notable": s.notable,
                        "source": _source(s.source),
                    }
                    for s in items
                ],
            }
            for label, items in issue.grouped_situations(
                editorial["sections"]["situations"].get("stages", {})
            )
        ],
        "cases": [
            {
                "jurisdiction": c.jurisdiction,
                "name": c.name,
                "citation": c.citation,
                "meta_line": _case_meta(c),
                "bottom_line": c.bottom_line,
                "facts": c.facts,
                "question": c.question,
                "holding": c.holding,
                "why_it_matters": c.why_it_matters,
                "background": c.background,
                "source": _source(c.source),
            }
            for c in issue.cases
        ],
        "concepts": (
            None
            if issue.concepts is None
            else {
                "pairing": issue.concepts.pairing,
                "sides": [
                    {
                        "label": side,
                        "term": concept.term,
                        "body": concept.body,
                        "see_also": concept.see_also,
                    }
                    for side, concept in issue.concepts.pair()
                ],
            }
        ),
        "numbers": [
            {
                "label": n.label,
                "value": n.value,
                "period": n.period,
                "change": n.change,
                "source": _source(n.source),
            }
            for n in issue.numbers
        ],
        "watchlist": [
            {
                "jurisdiction": w.jurisdiction,
                "text": w.text,
                "date_label": f"{w.date:%-d %b}" if w.date else "—",
            }
            for w in issue.watchlist
        ],
    }


def pdf_name(issue: Issue, editorial: dict) -> str:
    """The download filename. Derived from the config so a rename of the
    publication carries through to every link without a code change."""
    prefix = editorial["publication"].get("file_prefix", "issue")
    return f"{prefix}-{issue.slug}.pdf"


def render(issue: Issue, editorial: dict, out_dir: Path = OUTPUT_DIR) -> Path:
    if shutil.which("typst") is None:
        raise SystemExit(
            "typst is not on PATH.\n"
            "  Local:  see README.md → Running it locally\n"
            "  CI:     the publish workflow installs it"
        )

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = issue_to_dict(issue, editorial)
    (BUILD_DIR / "issue.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    out_path = out_dir / pdf_name(issue, editorial)
    subprocess.run(
        ["typst", "compile", "--root", str(REPO_ROOT), str(TEMPLATE), str(out_path)],
        check=True,
    )
    return out_path


def main(argv: list[str]) -> int:
    editorial = load_config("editorial")
    paths = [Path(a) for a in argv[1:]] or issue_paths()
    for path in paths:
        issue = load_issue(path)
        out = render(issue, editorial)
        size_kb = out.stat().st_size / 1024
        print(f"  {out.relative_to(REPO_ROOT)}  ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
