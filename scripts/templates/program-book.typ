// NECB 2026 — Program Book template.
// Half-letter (5.5 × 8.5 in), so a Letter or A4 sheet prints 2-up.
// Same NECB palette as scripts/templates/packet.typ; speaker cards
// render as photo-left / bio-right, and every abstract H3 starts a
// new page via a helper block emitted by build_program_book.py.

#let c-fuchsia = rgb("#B31E4B")
#let c-navy    = rgb("#1C3D7B")
#let c-teal    = rgb("#3B7368")
#let c-ink     = rgb("#14141A")
#let c-muted   = rgb("#6B6B6E")
#let c-rule    = rgb("#E1E1E4")
#let c-zebra   = rgb("#F7F7F6")

#set document(title: "NECB 2026 · Program Book")

#set page(
  width: 5.5in,
  height: 8.5in,
  margin: (x: 0.55in, top: 0.7in, bottom: 0.65in),
  header: context {
    // Emit a running header everywhere except the cover + TOC.
    let n = here().page()
    if n <= 2 { return [] }
    // Nearest ancestor H1 = the part we're inside.
    let h1 = query(selector(heading.where(level: 1)).before(here())).at(-1, default: none)
    // Nearest ancestor H2 = the day/section within that part.
    let h2 = query(selector(heading.where(level: 2)).before(here())).at(-1, default: none)
    let part_txt = if h1 != none { h1.body } else { [] }
    let section_txt = if h2 != none [
      #text(fill: c-muted)[  ·  ]
      #h2.body
    ] else { [] }
    set text(font: "Avenir Next", size: 8pt, fill: c-muted)
    grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      [#part_txt #section_txt],
      [NECB 2026],
    )
    v(2pt, weak: true)
    line(length: 100%, stroke: 0.4pt + c-rule)
  },
  footer: context {
    let n = here().page()
    if n > 1 {
      set text(font: "Avenir Next", size: 8pt, fill: c-muted)
      grid(
        columns: (1fr, auto),
        align: (left, right),
        [October 1–2, 2026 · Cambridge, MA],
        [#n of #counter(page).final().first()],
      )
    }
  },
)

#set text(font: "Charter", size: 9.8pt, fill: c-ink, lang: "en")
#set par(leading: 0.6em, spacing: 0.9em, justify: false)
#set list(indent: 0.5em, spacing: 0.55em, marker: text(fill: c-fuchsia, [•]))
#set enum(indent: 0.5em, spacing: 0.55em)
#set terms(hanging-indent: 1.3em)

#show link: it => text(fill: c-navy, it)
#show raw: it => text(font: "Menlo", size: 0.88em, fill: c-fuchsia, it)

// --- headings -------------------------------------------------------------
// Every H1 opens a new page (cover, then each Part).
#let h1-seen = counter("h1-seen")
#show heading.where(level: 1): it => {
  context { if h1-seen.get().first() > 0 { pagebreak(weak: true) } }
  h1-seen.step()
  block(above: 0pt, below: 14pt)[
    #set text(font: "Avenir Next", size: 18pt, weight: 700, fill: c-fuchsia)
    #it.body
    #v(6pt, weak: true)
    #line(length: 100%, stroke: 1.8pt + c-fuchsia)
  ]
}

// Day-banner headings from the poster part carry a <day> label so we
// can suppress their default heading render (the visible banner is
// drawn by #day-banner just before this heading emits its outline
// entry). Without this the label would render again in default H2
// style right after the banner page.
#show heading.where(level: 2): it => if it.label == <day> {
  // no-op body; the outline entry still registers via the heading itself.
  []
} else {
  block(above: 16pt, below: 7pt, sticky: true)[
    #set text(font: "Avenir Next", size: 12pt, weight: 700, fill: c-navy)
    #it.body
  ]
}

// H3 = abstract entries + schedule slots. Slightly larger and darker so
// each abstract's heading reads as the anchor of its page.
#show heading.where(level: 3): it => block(above: 0pt, below: 6pt, sticky: true)[
  #set text(font: "Avenir Next", size: 11pt, weight: 700, fill: c-teal)
  #it.body
]

// Day banner — emitted directly by the builder for the Poster
// Presentations part so Day 1 and Day 2 open on fresh, unmistakable
// section pages.
#let day-banner(label) = {
  pagebreak(weak: true)
  v(1in)
  align(center)[
    #text(font: "Avenir Next", size: 26pt, weight: 700, fill: c-fuchsia)[#label]
    #v(10pt, weak: true)
    #line(length: 40%, stroke: 1.5pt + c-fuchsia)
  ]
  v(0.3in)
}

#show heading.where(level: 4): it => block(above: 8pt, below: 3pt, sticky: true)[
  #set text(font: "Avenir Next", size: 9.5pt, weight: 700, fill: c-navy)
  #it.body
]

// Emphasis
#show strong: it => text(weight: 700, fill: c-navy, it)
#show emph: it => text(style: "italic", fill: c-muted, it)

// Rule helper used before abstract blocks.
#let divider() = block(above: 8pt, below: 8pt)[
  #line(length: 100%, stroke: 0.6pt + c-rule)
]

// --- tables ---------------------------------------------------------------
#set table(
  inset: (x: 9pt, y: 5.5pt),
  stroke: none,
  fill: (x, y) => if y == 0 { c-navy } else if calc.odd(y) { c-zebra } else { white },
)
#show table.cell.where(y: 0): set text(
  font: "Avenir Next", size: 9pt, weight: 600, fill: white,
)
#show figure: set block(breakable: true)
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: image): set figure.caption(position: bottom)

// --- horizontal rules -----------------------------------------------------
#let horizontalrule = block(
  above: 14pt, below: 14pt,
  align(center, line(length: 40%, stroke: 0.6pt + c-rule)),
)

// Speaker card: photo-left, name + affiliation + bio right. Used from
// the markdown as a raw {=typst} block per speaker.
#let speaker-card(photo: none, name: "", affiliation: "", bio: []) = block(
  breakable: false, above: 14pt, below: 10pt,
)[
  #grid(
    columns: (1.4in, 1fr),
    column-gutter: 0.35in,
    align: (top, top),
    if photo != none { image(photo, width: 1.35in) } else { [] },
    [
      #text(font: "Avenir Next", size: 12pt, weight: 700, fill: c-navy)[#name]
      #v(2pt, weak: true)
      #text(font: "Avenir Next", size: 8.5pt, fill: c-teal)[#affiliation]
      #v(6pt, weak: true)
      #set text(size: 9.5pt, fill: c-ink)
      #set par(leading: 0.55em, spacing: 0.7em)
      #bio
    ],
  )
]

$body$
