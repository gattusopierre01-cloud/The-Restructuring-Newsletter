// The Restructuring Brief — PDF template.
//
// Data comes from issue.json, written by pipeline/render_pdf.py, so this file
// holds only presentation. Compile with:
//
//   typst compile --root . templates/issue.typ out.pdf
//
// Fonts are Libertinus Serif and DejaVu Sans Mono, both embedded in Typst
// itself, so the PDF renders identically here and on a CI runner with no fonts
// installed.

#let d = json("/build/issue.json")

// -- palette ----------------------------------------------------------------

#let ink = rgb("#191919")
#let accent = rgb("#7a2230") // oxblood
#let gold = rgb("#b8862b")   // the crest's pale; used to mark the featured item
#let muted = rgb("#6d6a66")
#let hairline = rgb("#cdc8c0")
#let panel = rgb("#f6f4f1")

// -- page -------------------------------------------------------------------

#set document(title: d.doc_title, author: d.publication)

#set page(
  paper: "a4",
  margin: (x: 1.95cm, top: 1.8cm, bottom: 1.9cm),
  footer: context {
    let n = counter(page).get().first()
    line(length: 100%, stroke: 0.4pt + hairline)
    v(0.35em)
    grid(
      columns: (1fr, auto),
      align: (left, right),
      text(size: 7.5pt, fill: muted)[
        #d.publication · Issue #d.issue · Information and education only, not advice
      ],
      text(size: 7.5pt, fill: muted)[#n],
    )
  },
)

#set text(font: "Libertinus Serif", size: 10.5pt, fill: ink, lang: "en", region: "gb")
#set par(justify: true, leading: 0.62em, spacing: 0.8em)
#show link: set text(fill: accent)

// -- components -------------------------------------------------------------

#let tag(j) = box(
  inset: (x: 4pt, y: 1.5pt),
  outset: (y: 2pt),
  radius: 2pt,
  fill: accent,
  text(fill: white, size: 7pt, weight: "bold", tracking: 0.08em, font: "DejaVu Sans Mono")[#upper(j)],
)

// sticky: a section heading never sits alone at the foot of a page.
#let section-head(title, note: "") = block(
  above: 1.5em,
  below: 0.8em,
  width: 100%,
  sticky: true,
)[
  #line(length: 100%, stroke: 0.8pt + accent)
  #v(0.3em)
  #grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
    text(size: 9.5pt, weight: "bold", tracking: 0.18em, fill: accent)[#upper(title)],
    if note != "" { text(size: 8pt, fill: muted, style: "italic")[#note] } else { none },
  )
]

// The citation / venue line under a heading. Set in the body serif rather than
// a monospace face so it reads as a law-report reference, not as code.
#let meta(t) = text(size: 8.8pt, fill: muted, style: "italic")[#t]

// Run-in label, the way a law report sets one.
#let field(label, body) = par(justify: true)[
  #text(size: 8pt, weight: "bold", tracking: 0.07em, fill: accent)[#upper(label)]
  #h(0.45em)
  #body
]

#let source-line(src) = if src != none [
  #text(size: 8pt, fill: muted)[→ #link(src.url)[#src.title]]
]

// -- masthead ---------------------------------------------------------------

#block(width: 100%)[
  #line(length: 100%, stroke: 1.6pt + ink)
  #v(0.55em)
  #align(center)[
    // The crest. Centred above the wordmark on page one; the running footer
    // stays text-only so it costs nothing on later pages.
    #image("/assets/crest.svg", height: 15mm)
    #v(0.5em)
    #text(size: 25pt, weight: "bold", tracking: 0.04em)[#upper(d.publication)]
    #v(0.3em)
    #text(size: 9pt, fill: muted, tracking: 0.05em)[#d.strapline]
  ]
  #v(0.6em)
  #line(length: 100%, stroke: 0.6pt + ink)
  #v(0.3em)
  #grid(
    columns: (1fr, 1fr, 1fr),
    align: (left, center, right),
    text(size: 8pt, fill: muted)[Issue #d.issue],
    text(size: 8pt, fill: muted)[#d.period_label],
    text(size: 8pt, fill: muted)[#d.read_minutes minute read],
  )
  #v(0.2em)
  #line(length: 100%, stroke: 1.6pt + ink)
]

#if d.specimen_notice != "" {
  block(
    width: 100%,
    fill: rgb("#fbf3e6"),
    stroke: (left: 2.5pt + rgb("#b8862b")),
    inset: (x: 10pt, y: 8pt),
    above: 1.1em,
    below: 0.4em,
  )[
    #text(size: 8pt, weight: "bold", tracking: 0.12em, fill: rgb("#8a6418"))[SPECIMEN ISSUE]
    #v(0.3em)
    #text(size: 9pt)[#d.specimen_notice]
  ]
}

// -- the week in three lines -------------------------------------------------

#section-head(d.labels.headlines)

#for (i, h) in d.headlines.enumerate() [
  #grid(
    columns: (1.1em, 1fr),
    gutter: 0.5em,
    text(size: 10pt, weight: "bold", fill: accent)[#(i + 1)],
    text(size: 10.5pt)[#h],
  )
  #v(0.45em)
]

// -- situation of the week ---------------------------------------------------

#if d.featured != none {
  section-head(d.labels.featured)
  block(
    width: 100%,
    stroke: (left: 2.5pt + gold, rest: 0.5pt + hairline),
    inset: (x: 12pt, y: 11pt),
    below: 1.1em,
    breakable: true,
  )[
    #block(breakable: false, width: 100%)[
      #tag(d.featured.jurisdiction)
      #h(5pt)
      #text(size: 13pt, weight: "bold")[#d.featured.name]
      #h(4pt)
      #text(size: 9pt, fill: muted)[— #d.featured.kind]
      #v(0.25em)
      #meta(d.featured.meta_line)
    ]
    #v(0.5em)
    #text(size: 10.2pt)[#d.featured.body]
    #v(0.35em)
    #source-line(d.featured.source)
  ]
}

// -- situations --------------------------------------------------------------

#if d.situation_groups.len() > 0 {
  section-head(d.labels.situations, note: "restructurings worldwide, by stage")

  for group in d.situation_groups [
    // Stage label, set as a rule with the name sitting on it.
    #block(width: 100%, sticky: true, above: 0.9em, below: 0.6em)[
      #grid(
        columns: (auto, 1fr),
        gutter: 7pt,
        align: (left + horizon, left + horizon),
        text(size: 8pt, weight: "bold", tracking: 0.14em, fill: muted)[#upper(group.label)],
        line(length: 100%, stroke: 0.5pt + hairline),
      )
    ]

    #for item in group.items [
      #block(width: 100%, breakable: false, below: 0.95em)[
        #tag(item.jurisdiction)
        #h(5pt)
        #text(size: 11.5pt, weight: "bold")[#item.name]
        #h(4pt)
        #text(size: 9pt, fill: muted)[— #item.kind]
        #v(0.25em)
        #meta(item.meta_line)
        #v(0.3em)
        #text(size: 10pt)[#item.notable]
        #v(0.25em)
        #source-line(item.source)
      ]
    ]
  ]
}

// -- case notes --------------------------------------------------------------

#section-head(
  d.labels.cases,
  note: "United Kingdom and United States only",
)

#for c in d.cases [
  #block(
    width: 100%,
    fill: panel,
    stroke: (left: 2.5pt + accent),
    inset: (x: 11pt, y: 10pt),
    below: 1.1em,
    breakable: true,
  )[
    // Heading and bottom line stay together: a case name stranded at the foot
    // of a page with its holding overleaf is worse than a half-empty page.
    #block(breakable: false, width: 100%)[
      #tag(c.jurisdiction)
      #h(5pt)
      #text(size: 12pt, weight: "bold")[#c.name]
      #v(0.25em)
      #meta(c.meta_line)
      #v(0.5em)

      #block(
        width: 100%,
        fill: white,
        inset: (x: 8pt, y: 7pt),
        radius: 2pt,
      )[
        #text(size: 8pt, weight: "bold", tracking: 0.1em, fill: accent)[BOTTOM LINE]
        #v(0.25em)
        #text(size: 10.5pt, weight: "semibold")[#c.bottom_line]
      ]
    ]
    #v(0.55em)

    #set text(size: 9.8pt)
    #field("Facts", c.facts)
    #field("Question", c.question)
    #field("Holding", c.holding)
    #field("Why it matters", c.why_it_matters)

    #v(0.3em)
    #block(
      width: 100%,
      inset: (left: 8pt),
      stroke: (left: 1pt + hairline),
    )[
      #text(size: 8pt, weight: "bold", tracking: 0.07em, fill: muted)[BACKGROUND]
      #h(0.45em)
      #text(size: 9.3pt, fill: rgb("#3d3a37"))[#c.background]
    ]
    #v(0.4em)
    #source-line(c.source)
  ]
]

// -- both sides of the table -------------------------------------------------

// Two columns side by side, so the pairing is visible before either is read.
// The grid's own fill gives both cells the height of the taller one, which a
// pair of separate blocks would not.
#if d.concepts != none {
  section-head(d.labels.concepts, note: "one from each seat")
  block(width: 100%, breakable: false)[
    #grid(
      columns: (1fr, 1fr),
      gutter: 11pt,
      fill: panel,
      inset: (x: 10pt, y: 9pt),
      ..d.concepts.sides.map(side => [
        #text(size: 8pt, weight: "bold", tracking: 0.14em, fill: accent)[#upper(side.label)]
        #v(0.3em)
        #text(size: 12pt, weight: "bold")[#side.term]
        #v(0.4em)
        #text(size: 9.6pt)[#side.body]
        #if side.see_also.len() > 0 [
          #v(0.4em)
          #text(size: 8pt, fill: muted, style: "italic")[
            See also: #side.see_also.join(" · ")
          ]
        ]
      ]),
    )
    #if d.concepts.pairing != "" [
      #v(0.6em)
      #block(
        width: 100%,
        inset: (left: 8pt),
        stroke: (left: 2pt + gold),
      )[
        #text(size: 9.4pt, style: "italic", fill: rgb("#3d3a37"))[#d.concepts.pairing]
      ]
    ]
  ]
}

// -- numbers -----------------------------------------------------------------

#if d.numbers.len() > 0 {
  section-head("Numbers")
  table(
    columns: (1fr, auto, auto),
    align: (left + horizon, right + horizon, right + horizon),
    stroke: none,
    inset: (x: 5pt, y: 6pt),
    fill: (_, row) => if row == 0 { panel } else { none },
    table.header(
      text(size: 8pt, weight: "bold", tracking: 0.1em, fill: accent)[INDICATOR],
      text(size: 8pt, weight: "bold", tracking: 0.1em, fill: accent)[LATEST],
      text(size: 8pt, weight: "bold", tracking: 0.1em, fill: accent)[PERIOD],
    ),
    ..d.numbers.map(n => (
      [
        #text(size: 9.8pt)[#n.label]
        #if n.source != none [
          #linebreak()
          #text(size: 7.5pt, fill: muted)[#link(n.source.url)[#n.source.title]]
        ]
      ],
      text(size: 9.8pt, weight: "bold")[#n.value],
      text(size: 9pt, fill: muted)[#n.period],
    )).flatten(),
  )
  line(length: 100%, stroke: 0.4pt + hairline)
}

// -- watchlist ---------------------------------------------------------------

#if d.watchlist.len() > 0 {
  section-head("Watchlist")
  for w in d.watchlist [
    #grid(
      columns: (auto, auto, 1fr),
      gutter: 0.6em,
      align: (left + top, left + top, left + top),
      text(size: 8.5pt, fill: muted)[#w.date_label],
      tag(w.jurisdiction),
      text(size: 9.8pt)[#w.text],
    )
    #v(0.4em)
  ]
}

// -- colophon ----------------------------------------------------------------

#v(1.2em)
#line(length: 100%, stroke: 0.8pt + ink)
#v(0.5em)
#block(width: 100%)[
  #text(size: 8.2pt, fill: muted)[#d.disclaimer]
  #v(0.5em)
  #text(size: 8.5pt)[
    Archive and subscribe: #link(d.site_url)[#d.site_url_label]
  ]
]
