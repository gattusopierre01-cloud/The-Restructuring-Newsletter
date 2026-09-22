# The Restructuring Brief

A weekly newsletter on restructuring and insolvency in the UK and US: notable
filings and deals read from a finance point of view, and short notes on the
court decisions that shape how those deals get done. Written for practitioners
and students at the same time — the bottom line first, the doctrine explained
underneath.

Each issue is written once and published three ways:

| Output | Where it goes | Built by |
| --- | --- | --- |
| Website | GitHub Pages — archive, glossary, signup | MkDocs Material |
| PDF | For posting to LinkedIn and for printing | Typst |
| Email | Subscribers | Buttondown |

## How it works

```
 issues/2026-W40.yaml          one file per issue: structured data, not prose
         │
         ├── pipeline/validate.py      editorial rules, enforced in CI
         ├── pipeline/render_pdf.py    → docs/pdf/…pdf      (via templates/issue.typ)
         ├── pipeline/render_site.py   → docs/…md           (built by MkDocs)
         └── pipeline/render_email.py  → Buttondown
```

The weekly cycle:

1. `draft.yml` runs on a schedule, collects the week's developments from public
   sources and opens a pull request with a skeleton issue.
2. You read it, correct it and fill in what is missing.
3. Merging it deploys the website and renders the PDF.
4. Sending the email is a separate, manual step.

**A person merges every issue.** That is the point of the design. Automation
can find a judgment, extract a citation and check a word budget. It cannot tell
you that a summary of a holding is wrong, and in this subject that is the
failure that matters. CI catches the mechanical problems so that review time
goes on the substance.

## The issue file

Everything lives in one YAML file per issue, as fields rather than free text.
That is what keeps the three outputs identical in substance and lets the
validator check a draft before anyone reads it.

```yaml
issue: 1
slug: 2026-W40
status: published          # specimen | draft | published
period_start: 2026-09-28
period_end: 2026-10-04

headlines: [...]           # the week in three lines
deals: [...]               # filings and deals, finance view
cases: [...]               # bottom line → facts → question → holding → why → background
concept: {...}             # one concept explained from first principles
numbers: [...]             # indicators, tracked week to week
watchlist: [...]           # what is coming up
```

`issues/2026-W39.yaml` is a specimen issue, written by hand to settle the
format. It uses two landmark decisions rather than current news, and it is
marked as a specimen wherever it appears.

## Editorial rules

The rules live in [`config/editorial.yaml`](config/editorial.yaml), not in the
Python, so they can be changed without touching code. `pipeline/validate.py`
enforces them and fails the build on a breach.

The two that matter most:

- **Every case note links to the judgment itself.** Law-firm commentary is used
  to find decisions and to sanity check a reading of one. It is never the cited
  authority for what a court held.
- **No paywalled sources.** Students are half the audience and cannot reach
  them.

The rest are word budgets per section, citation formats, and a short list of
adjectives that tend to stand in for analysis.

## Running it locally

```bash
git clone https://github.com/gattusopierre01-cloud/The-Restructuring-Newsletter.git
cd The-Restructuring-Newsletter
pip install -r requirements.txt

# Typst, for the PDF (Linux; see typst.app for macOS and Windows)
curl -fsSL https://github.com/typst/typst/releases/download/v0.15.1/typst-x86_64-unknown-linux-musl.tar.xz \
  | tar -xJ && sudo install typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst
```

Then:

```bash
python -m pipeline.validate                    # check every issue
python -m pipeline.render_pdf                  # → docs/pdf/
python -m pipeline.render_site                 # → docs/
mkdocs serve                                   # preview at localhost:8000

python -m pipeline.render_email issues/2026-W39.yaml   # print the email, don't send

python -m pipeline.collect                     # see what this week's sources have
python -m pipeline.new_issue                   # start next week's file
```

The PDF uses Libertinus Serif, which ships inside Typst, so it renders
identically on your machine and on a CI runner with no fonts installed.

## Setting it up

Four things, in this order. Only the first is needed to see the site.

**1. GitHub Pages.** Settings → Pages → Source: *GitHub Actions*. Push to
`main` and the Publish workflow deploys the site.

**2. Buttondown**, for email. Create an account, put your username in
`config/editorial.yaml` under `email.username`, and add your API key as a
repository secret named `BUTTONDOWN_API_KEY` (Settings → Secrets and variables
→ Actions).

**3. CourtListener**, for US opinions. A free API token, added as
`COURTLISTENER_TOKEN`. Not needed until the US collector is switched on.

**4. Anthropic**, for the drafting step in phase 4. `ANTHROPIC_API_KEY`.

Secrets go in GitHub, never in the repository.

## Where this has got to

- [x] **Phase 1** — issue format, PDF template, website, specimen issue
- [x] **Phase 2** — publishing: site and PDF on merge, email send as a manual step
- [ ] **Phase 3** — collectors. EDGAR and Find Case Law are written and can be
      run by hand; they have not yet been watched over a full week, and
      CourtListener, the Insolvency Service and the Gazette are not written yet
- [ ] **Phase 4** — drafting: an LLM fills the issue fields from the candidates
- [ ] **Phase 5** — the weekly pull request, on a schedule
- [ ] **Phase 6** — topic tags on case notes, a maturity-wall watchlist, a
      custom domain

## Turning on automatic sending

Sending is manual on purpose while the pipeline is new. To make it automatic,
add a job to `publish.yml` that runs `render_email --send` when an issue's
`status` is `published` and it was added in that push. Keep the validation step
in front of it. It is worth waiting until a few issues have gone out by hand.

## Layout

```
config/          editorial rules and the source list — change things here
issues/          one YAML file per issue: the source of truth
pipeline/        loading, validation, rendering, collectors
templates/       issue.typ — the PDF layout
docs/            website; about.md and the stylesheet are the only hand-written files
.github/         publish, send-email, draft
```

## Corrections

Corrections matter more than speed here. Open an issue, and it is fixed on the
website and noted in the next edition.

## Licence

Code: MIT. Editorial content: © the author, all rights reserved.
