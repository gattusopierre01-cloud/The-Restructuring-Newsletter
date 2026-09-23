// The Restructuring Brief — PDF template.
//
// Data comes from issue.json, written by pipeline/render_pdf.py, so this file
// holds only presentation. Compile with:
//
//   typst compile --root . templates/issue.typ out.pdf
//
// Fonts are Libertinus Serif and DejaVu Sans Mono, both embedded in Typst
// itself, so the PDF renders identically here and on a CI runner with no fonts
// installed. The crest is assets/crest.svg, shared with the website.
//
// Three decisions worth knowing before changing anything:
//
//   Ragged right, not justified. Justified serif on this measure opens rivers
//   of white down a paragraph, which is what made earlier drafts feel dense.
//
//   Field labels sit above their text rather than running in, so a reader can
//   find the holding without reading the facts.
//
//   Items are breakable, with their heading and reference line held together.
//   An unbreakable item that will not fit jumps whole to the next page and
//   leaves a hole behind it.

#let d = json("/build/issue.json")

#let ink = rgb("#191919")
#let accent = rgb("#7a2230")
#let gold = rgb("#b8862b")
#let muted = rgb("#6d6a66")
#let hairline = rgb("#cdc8c0")

#set document(title: d.doc_title, author: d.publication)
#set page(
  paper: "a4",
  margin: (x: 1.9cm, top: 1.5cm, bottom: 1.75cm),
  footer: context {
    let n = counter(page).get().first()
    line(length: 100%, stroke: 0.4pt + hairline)
    v(0.3em)
    grid(
      columns: (auto, 1fr, auto),
      column-gutter: 7pt,
      align: (left + horizon, left + horizon, right + horizon),
      // The crest returns small on every page after the first, so the
      // document is recognisable wherever it falls open.
      if n > 1 { image("/assets/crest.svg", height: 4.6mm) } else { none },
      text(size: 7.5pt, fill: muted)[#d.publication · Issue #d.issue · Information and education only, not advice],
      text(size: 7.5pt, fill: muted)[#n],
    )
  },
)

#set text(font: "Libertinus Serif", size: 10.6pt, fill: ink, lang: "en", region: "gb")
#set par(justify: false, leading: 0.75em, spacing: 0.9em)
#show link: set text(fill: accent)

#let tag(j) = box(
  inset: (x: 4pt, y: 1.5pt), outset: (y: 2pt), radius: 2pt, fill: accent,
  text(fill: white, size: 7pt, weight: "bold", tracking: 0.08em, font: "DejaVu Sans Mono")[#upper(j)],
)

#let section-head(title, note: "") = block(above: 1.3em, below: 0.7em, width: 100%, sticky: true)[
  #grid(
    columns: (1fr, auto), align: (left + bottom, right + bottom),
    text(size: 10pt, weight: "bold", tracking: 0.2em, fill: accent)[#upper(title)],
    if note != "" { text(size: 8pt, fill: muted, style: "italic")[#note] } else { none },
  )
  #v(0.32em)
  #line(length: 100%, stroke: 0.6pt + accent)
]

#let meta(t) = text(size: 8.6pt, fill: muted)[#t]

// Label above its text, not run in: each part of the note is findable.
#let field(label, body) = block(below: 0.55em, width: 100%)[
  #text(size: 7.2pt, weight: "bold", tracking: 0.16em, fill: accent)[#upper(label)]
  #v(0.14em)
  #par(justify: false)[#body]
]

#let source-line(src) = if src != none [
  #text(size: 8.2pt, fill: muted)[→ #link(src.url)[#src.title]]
]

// -- masthead ----------------------------------------------------------------

#block(width: 100%)[
  #grid(
    columns: (auto, 1fr, auto),
    column-gutter: 15pt,
    align: (left + horizon, left + horizon, right + bottom),
    image("/assets/crest.svg", height: 15mm),
    [
      #text(size: 23pt, weight: "bold", tracking: 0.04em)[#upper(d.publication)]
      #v(0.2em)
      #text(size: 9pt, fill: muted, style: "italic")[#d.strapline]
    ],
    text(size: 8pt, fill: muted)[
      Issue #d.issue
      #linebreak()
      #d.period_label
      #linebreak()
      #d.read_minutes minute read
    ],
  )
  #v(0.45em)
  #line(length: 100%, stroke: 0.9pt + ink)
]

#if d.specimen_notice != "" {
  block(width: 100%, stroke: (left: 2.5pt + gold), inset: (x: 11pt, y: 7pt),
        above: 1.1em, below: 0.4em)[
    #text(size: 8pt, weight: "bold", tracking: 0.12em, fill: rgb("#8a6418"))[SPECIMEN ISSUE]
    #v(0.25em)
    #text(size: 9.5pt)[#d.specimen_notice]
  ]
}

#section-head(d.labels.headlines)

#for (i, h) in d.headlines.enumerate() [
  #grid(
    columns: (1.4em, 1fr), gutter: 0.5em,
    text(size: 10.5pt, weight: "bold", fill: accent)[#(i + 1)],
    text(size: 11pt)[#h],
  )
  #v(0.45em)
]

// -- situation of the week ---------------------------------------------------

#if d.featured != none {
  section-head(d.labels.featured)
  block(width: 100%, below: 1.0em, breakable: true)[
    #block(breakable: false, width: 100%)[
      #tag(d.featured.jurisdiction)
      #h(6pt)
      #text(size: 14pt, weight: "bold")[#d.featured.name]
      #v(0.3em)
      #text(size: 9pt, fill: accent)[#d.featured.kind]
      #v(0.25em)
      #meta(d.featured.meta_line)
    ]
    #v(0.7em)
    #for para in d.featured.paragraphs [
      #par(justify: false)[#text(size: 10.5pt)[#para]]
      #v(0.45em)
    ]
    #source-line(d.featured.source)
  ]
}

// -- situations --------------------------------------------------------------

#if d.situation_groups.len() > 0 {
  section-head(d.labels.situations, note: "restructurings worldwide, by stage")

  for group in d.situation_groups [
    #block(width: 100%, sticky: true, above: 0.9em, below: 0.75em)[
      #text(size: 7.5pt, weight: "bold", tracking: 0.18em, fill: muted)[#upper(group.label)]
    ]

    #for item in group.items [
      #block(width: 100%, breakable: true, below: 0.85em)[
        #block(breakable: false, width: 100%)[
          #tag(item.jurisdiction)
          #h(6pt)
          #text(size: 12.5pt, weight: "bold")[#item.name]
          #v(0.25em)
          #text(size: 8.8pt, fill: accent)[#item.kind]
          #v(0.22em)
          #meta(item.meta_line)
        ]
        #v(0.5em)
        #par(justify: false)[#text(size: 10.5pt)[#item.notable]]
        #v(0.35em)
        #source-line(item.source)
      ]
    ]
  ]
}

// -- case notes --------------------------------------------------------------

#section-head(d.labels.cases, note: "United Kingdom and United States only")

#for c in d.cases [
  #block(width: 100%, stroke: (left: 3pt + accent), inset: (x: 14pt, y: 4pt),
         below: 1.1em, breakable: true)[
    #block(breakable: false, width: 100%)[
      #tag(c.jurisdiction)
      #h(6pt)
      #text(size: 13pt, weight: "bold")[#c.name]
      #v(0.28em)
      #meta(c.meta_line)
      #v(0.7em)
      #line(length: 100%, stroke: 0.5pt + hairline)
      #v(0.5em)
      #text(size: 11.5pt, weight: "semibold")[#c.bottom_line]
      #v(0.5em)
      #line(length: 100%, stroke: 0.5pt + hairline)
    ]
    #v(0.8em)
    #set text(size: 10.2pt)
    #field("Facts", c.facts)
    #field("Question", c.question)
    #field("Holding", c.holding)
    #field("Why it matters", c.why_it_matters)
    #block(below: 0.7em, width: 100%)[
      #text(size: 7.2pt, weight: "bold", tracking: 0.16em, fill: muted)[BACKGROUND]
      #v(0.22em)
      #par(justify: false)[#text(size: 9.8pt, fill: rgb("#45413d"))[#c.background]]
    ]
    #source-line(c.source)
  ]
]

// -- both sides of the table -------------------------------------------------

#if d.concepts != none {
  section-head(d.labels.concepts, note: "one from each seat")
  block(width: 100%, breakable: false)[
    #grid(
      columns: (1fr, 1fr), gutter: 18pt,
      ..d.concepts.sides.map(side => [
        #line(length: 100%, stroke: 1.5pt + accent)
        #v(0.4em)
        #text(size: 7.5pt, weight: "bold", tracking: 0.18em, fill: accent)[#upper(side.label)]
        #v(0.35em)
        #text(size: 12.5pt, weight: "bold")[#side.term]
        #v(0.45em)
        #par(justify: false)[#text(size: 10pt)[#side.body]]
        #if side.see_also.len() > 0 [
          #v(0.45em)
          #text(size: 8pt, fill: muted, style: "italic")[See also: #side.see_also.join(" · ")]
        ]
      ]),
    )
    #if d.concepts.pairing != "" [
      #v(0.9em)
      #block(width: 100%, inset: (left: 10pt), stroke: (left: 2pt + gold))[
        #text(size: 10pt, style: "italic", fill: rgb("#45413d"))[#d.concepts.pairing]
      ]
    ]
  ]
}

// -- numbers -----------------------------------------------------------------

#if d.numbers.len() > 0 {
  section-head(d.labels.numbers)
  table(
    columns: (1fr, auto, auto), align: (left + horizon, right + horizon, right + horizon),
    stroke: (x, y) => (bottom: 0.4pt + hairline), inset: (x: 2pt, y: 9pt),
    table.header(
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[INDICATOR],
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[LATEST],
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[PERIOD],
    ),
    ..d.numbers.map(n => (
      [
        #text(size: 10.2pt)[#n.label]
        #if n.source != none [
          #linebreak()
          #text(size: 7.8pt, fill: muted)[#link(n.source.url)[#n.source.title]]
        ]
      ],
      text(size: 10.2pt, weight: "bold")[#n.value],
      text(size: 9.2pt, fill: muted)[#n.period],
    )).flatten(),
  )
}

// -- watchlist ---------------------------------------------------------------

#if d.watchlist.len() > 0 {
  section-head(d.labels.watchlist)
  for w in d.watchlist [
    #grid(
      columns: (auto, auto, 1fr), gutter: 0.7em,
      align: (left + top, left + top, left + top),
      text(size: 8.5pt, fill: muted)[#w.date_label],
      tag(w.jurisdiction),
      text(size: 10.3pt)[#w.text],
    )
    #v(0.6em)
  ]
}

#v(1.0em)
#line(length: 100%, stroke: 0.8pt + ink)
#v(0.5em)
#block(width: 100%)[
  #text(size: 8.4pt, fill: muted)[#d.disclaimer]
  #v(0.5em)
  #text(size: 8.6pt)[Archive and subscribe: #link(d.site_url)[#d.site_url_label]]
]
