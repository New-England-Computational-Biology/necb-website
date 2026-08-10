// NECB 2026 — print template for reviewer-facing documents.
// Used as a pandoc typst template: pandoc -t typst --template=this.
// Palette mirrors assets/css/main.css (fuchsia / navy / teal).

#let c-fuchsia = rgb("#B31E4B")
#let c-navy    = rgb("#1C3D7B")
#let c-teal    = rgb("#3B7368")
#let c-ink     = rgb("#14141A")
#let c-muted   = rgb("#6B6B6E")
#let c-rule    = rgb("#E1E1E4")
#let c-zebra   = rgb("#F7F7F6")

#set document(title: "NECB 2026 · Reviewer Packet")

#set page(
  paper: "us-letter",
  margin: (x: 1in, top: 0.95in, bottom: 0.9in),
  footer: context {
    let n = here().page()
    if n > 1 {
      set text(font: "Avenir Next", size: 8.5pt, fill: c-muted)
      grid(
        columns: (1fr, auto),
        align: (left, right),
        [NECB 2026 · Reviewer Packet],
        [#n of #counter(page).final().first()],
      )
    }
  },
)

#set text(font: "Charter", size: 10.5pt, fill: c-ink, lang: "en")
#set par(leading: 0.68em, spacing: 1.1em, justify: false)
#set list(indent: 0.5em, spacing: 0.7em, marker: text(fill: c-fuchsia, [•]))
#set enum(indent: 0.5em, spacing: 0.7em)
#set terms(hanging-indent: 1.5em)

#show link: it => text(fill: c-navy, it)
#show raw: it => text(font: "Menlo", size: 0.88em, fill: c-fuchsia, it)

// --- headings -------------------------------------------------------------
// Each level-1 heading opens a new page (cover, Part 1, Part 2).
#let h1-seen = counter("h1-seen")
#show heading.where(level: 1): it => {
  context { if h1-seen.get().first() > 0 { pagebreak(weak: true) } }
  h1-seen.step()
  block(above: 0pt, below: 16pt)[
    #set text(font: "Avenir Next", size: 20pt, weight: 700, fill: c-fuchsia)
    #it.body
    #v(7pt, weak: true)
    #line(length: 100%, stroke: 2pt + c-fuchsia)
  ]
}

#show heading.where(level: 2): it => block(above: 20pt, below: 9pt, sticky: true)[
  #set text(font: "Avenir Next", size: 13pt, weight: 700, fill: c-navy)
  #it.body
]

#show heading.where(level: 3): it => block(above: 16pt, below: 7pt, sticky: true)[
  #set text(font: "Avenir Next", size: 10.5pt, weight: 700, fill: c-teal)
  #it.body
]

// --- block quotes (the "> prompt" line under each dimension) --------------
#show quote.where(block: true): it => block(
  width: 100%,
  above: 10pt,
  below: 12pt,
  inset: (left: 11pt, y: 1pt),
  stroke: (left: 2pt + c-teal),
  sticky: true, // keep the prompt with the score table that follows

  text(style: "italic", fill: rgb("#3A3A3E"), it.body),
)

// --- tables ---------------------------------------------------------------
#set table(
  inset: (x: 9pt, y: 5.5pt),
  stroke: none,
  fill: (x, y) => if y == 0 { c-navy } else if calc.odd(y) { c-zebra } else { white },
)
#show table.cell.where(y: 0): set text(
  font: "Avenir Next", size: 9.5pt, weight: 600, fill: white,
)
#show figure: set block(breakable: true)
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: image): set figure.caption(position: bottom)

// --- horizontal rules -----------------------------------------------------
#let horizontalrule = block(
  above: 18pt, below: 18pt,
  align(center, line(length: 40%, stroke: 0.6pt + c-rule)),
)
#let divider = () => horizontalrule

$body$
