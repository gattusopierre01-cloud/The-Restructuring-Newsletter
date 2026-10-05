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

#let section-head(title, note: "") = block(above: 1.05em, below: 0.6em, width: 100%, sticky: true)[
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
#let field(label, body) = block(above: 1.0em, below: 0.25em, width: 100%)[
  #text(size: 7.2pt, weight: "bold", tracking: 0.16em, fill: accent)[#upper(label)]
  #v(0.14em)
  #par(justify: false)[#body]
]

#let source-line(src) = if src != none [
  #text(size: 8.2pt, fill: muted)[→ #link(src.url)[#src.title]]
]

// -- masthead ----------------------------------------------------------------

#block(width: 100%)[
  // The wordmark must never wrap, and the width it gets depends on how long the
  // period label is. The budget, on a 172mm measure:
  //
  //   487.6pt text width
  //   - 36.5pt crest      - 30pt gutters      - ~101pt a long period label
  //   = ~320pt for the wordmark
  //
  // "THE RESTRUCTURING BRIEF" measures 344pt at 23pt and 299pt at 20pt, so 23pt
  // only ever fitted a short label and wrapped the moment a period ran across
  // two months. 20pt leaves about 20pt of headroom on the longest label likely.
  #grid(
    columns: (auto, 1fr, auto),
    column-gutter: 15pt,
    align: (left + horizon, left + horizon, right + bottom),
    image("/assets/crest.svg", height: 15mm),
    [
      #text(size: 20pt, weight: "bold", tracking: 0.04em)[#upper(d.publication)]
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
    #block(above: 1.0em, below: 0.6em, width: 100%)[
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
  // Unbreakable: the two sides are meant to be read level with each other,
  // which a page break destroys. It moves whole to the next page instead.
  block(width: 100%, breakable: false)[
    #grid(
      columns: (1fr, 1fr), gutter: 16pt,
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
      #v(0.7em)
      #block(width: 100%, inset: (left: 10pt), stroke: (left: 2pt + gold))[
        #text(size: 10pt, style: "italic", fill: rgb("#45413d"))[#d.concepts.pairing]
      ]
    ]
  ]
}

// -- numbers -----------------------------------------------------------------

#if d.conditions != "" or d.numbers.len() > 0 {
  section-head(d.labels.numbers, note: "what the market is pricing")
}

#if d.conditions != "" {
  block(width: 100%, below: 0.7em, breakable: true)[
    #par(justify: false)[#text(size: 10.5pt)[#d.conditions]]
  ]
}

#if d.numbers.len() > 0 {
  // Three columns: what it is, where it stands, which way it moved. The
  // direction is the part a reader acts on, so it gets a column of its own
  // rather than being buried under the value.
  table(
    columns: (1fr, auto, auto), align: (left + horizon, right + horizon, right + horizon),
    stroke: (x, y) => (bottom: 0.4pt + hairline), inset: (x: 2pt, y: 5.5pt),
    table.header(
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[INDICATOR],
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[LATEST],
      text(size: 7.5pt, weight: "bold", tracking: 0.16em, fill: accent)[ON THE WEEK],
    ),
    ..d.numbers.map(n => (
      [
        #text(size: 10.2pt)[#n.label]
        #if n.source != none [
          #linebreak()
          #text(size: 7.8pt, fill: muted)[
            #link(n.source.url)[#n.source.title]#if n.period != "" [ · #n.period]
          ]
        ]
      ],
      text(size: 10.2pt, weight: "bold")[#n.value],
      if n.change != none {
        text(size: 9pt, fill: muted)[#n.change]
      } else {
        text(size: 9pt, fill: muted)[—]
      },
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
    #v(0.45em)
  ]
}

// The colophon closes the newsletter proper, so it sits before the optional
// page rather than after it. The long view is a supplement with its own source
// note; trailing the colophon behind it stranded four lines on a page of their
// own whenever a feature ran.
#block(width: 100%, breakable: false, above: 0.55em)[
  #line(length: 100%, stroke: 0.8pt + ink)
  #v(0.32em)
  #text(size: 8.1pt, fill: muted)[#d.disclaimer]
  #v(0.32em)
  #text(size: 8.6pt)[Archive and subscribe: #link(d.site_url)[#d.site_url_label]]
]

// -- the long view -----------------------------------------------------------
//
// An optional fourth page, run only when the week gives it something. Nothing
// above this line changes when it is absent, which is the whole point: pages
// one to three are the newsletter, and this is the week it deserved more room.
//
// The chart draws itself from the numbers in the issue file. That is not a
// stylistic preference. Every issue is generated from content written days
// earlier, so anything positioned by hand would be wrong the following week.

#if d.feature != none {
  pagebreak()

  section-head(d.labels.feature, note: "stepping back from the week")

  block(width: 100%, below: 0.7em)[
    #text(size: 17pt, weight: "bold")[#d.feature.title]
  ]

  // -- the three furniture pieces, each defined once and placed by index ------
  //
  // Three figures at most in the strip, so each gets a third of the measure. A
  // move is two numbers and an arrow; printing only the latest throws the point
  // away.
  let stat-strip() = block(
    width: 100%, breakable: false, above: 0.6em, below: 0.8em,
    stroke: (top: 0.6pt + accent, bottom: 0.4pt + hairline),
    inset: (y: 8pt),
  )[
    #grid(
      columns: d.feature.stats.map(_ => 1fr),
      column-gutter: 12pt,
      ..d.feature.stats.map(s => [
        #text(size: 7.2pt, weight: "bold", tracking: 0.14em, fill: accent)[#upper(s.key)]
        #v(0.3em)
        #text(size: 12pt, weight: "bold")[#s.value]
        #if s.note != "" [
          #v(0.18em)
          #text(size: 7.8pt, fill: muted)[#s.note]
        ]
      ]),
    )
  ]

  // Horizontal bars, one series, labels left and values right. No gridlines and
  // no legend: with a single series the title names it, and a rule behind four
  // bars is furniture rather than information. Each bar's share of the longest
  // one is worked out in Python, so this only has to draw a rectangle.
  let figure-block(c) = block(width: 100%, breakable: false, above: 0.6em, below: 0.8em)[
    #text(size: 7.2pt, weight: "bold", tracking: 0.16em, fill: accent)[FIGURE]
    #v(0.25em)
    #text(size: 10.5pt, weight: "bold")[#c.title]
    #if c.note != "" [
      #v(0.15em)
      #text(size: 8.2pt, fill: muted)[#c.note]
    ]
    #v(0.7em)
    #grid(
      columns: (auto, 1fr, auto),
      column-gutter: 10pt,
      row-gutter: 7pt,
      align: (left + horizon, left + horizon, right + horizon),
      ..c.bars.map(b => (
        text(size: 9.2pt)[#b.label],
        box(width: 100%)[
          #box(width: b.fraction * 100%, height: 9pt,
               radius: (right: 2pt), fill: accent)
        ],
        text(size: 9.6pt, weight: "bold")[#b.display],
      )).flatten(),
    )
    #if c.source != none [
      #v(0.65em)
      #line(length: 100%, stroke: 0.4pt + hairline)
      #v(0.35em)
      #source-line(c.source)
    ]
  ]

  let quote-block(q) = block(
    width: 100%, inset: (left: 11pt), stroke: (left: 2pt + gold),
    above: 0.9em, below: 0.9em,
  )[
    #text(size: 11.5pt, style: "italic", fill: rgb("#45413d"))[#q.text]
    #if q.attribution != "" [
      #v(0.35em)
      #text(size: 8.4pt, fill: muted)[#q.attribution]
    ]
  ]

  // Walk the paragraphs, dropping each piece in after the paragraph it names.
  // Placement lives in the issue file rather than here, so a different week can
  // put the chart somewhere else without anyone touching the template.
  for (i, para) in d.feature.paragraphs.enumerate() {
    let n = i + 1
    par(justify: false)[
      #text(size: if i == 0 { 10.8pt } else { 10.2pt })[#para]
    ]
    v(0.38em)
    if d.feature.stats.len() > 0 and d.feature.stats_after == n { stat-strip() }
    if d.feature.chart != none and d.feature.chart.after == n {
      figure-block(d.feature.chart)
    }
    if d.feature.pull_quote != none and d.feature.pull_quote.after == n {
      quote-block(d.feature.pull_quote)
    }
  }

  if d.feature.sources != "" {
    block(width: 100%, above: 0.7em)[
      #line(length: 100%, stroke: 0.4pt + hairline)
      #v(0.3em)
      #text(size: 7.9pt, fill: muted)[→ #d.feature.sources]
    ]
  }
}
