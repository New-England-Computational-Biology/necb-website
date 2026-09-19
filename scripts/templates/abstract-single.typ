// NECB 2026 — Standalone Abstract template.
// Same half-letter geometry + palette as the program book, but with a
// minimal per-abstract chrome: NECB header line, per-abstract heading
// (fuchsia H1), presenter/authors/session block, abstract body. No book
// section context in the running header, no book-wide page numbering
// (footer just carries the date + venue).

#let c-fuchsia = rgb("#B31E4B")
#let c-navy    = rgb("#1C3D7B")
#let c-teal    = rgb("#3B7368")
#let c-ink     = rgb("#14141A")
#let c-muted   = rgb("#6B6B6E")
#let c-rule    = rgb("#E1E1E4")

#set document(title: "NECB 2026 · Abstract")

#set page(
  width: 5.5in,
  height: 8.5in,
  margin: (x: 0.55in, top: 0.6in, bottom: 0.5in),
  header: context {
    set text(font: "Avenir Next", size: 8pt, fill: c-muted)
    grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      [New England Computational Biology · October 1–2, 2026 · Cambridge, MA],
      text(weight: 700, fill: c-fuchsia)[NECB 2026],
    )
    v(2pt, weak: true)
    line(length: 100%, stroke: 0.4pt + c-rule)
  },
  footer: context {
    set text(font: "Avenir Next", size: 7.5pt, fill: c-muted)
    align(center)[newenglandcompbio.org]
  },
)

#set text(font: "Charter", size: 9.8pt, fill: c-ink, lang: "en")
#set par(leading: 0.6em, spacing: 0.9em, justify: true, linebreaks: "optimized")
#set list(indent: 0.5em, spacing: 0.55em, marker: text(fill: c-fuchsia, [•]))

#show link: it => text(fill: c-navy, it)
#show raw: it => text(font: "Menlo", size: 0.88em, fill: c-fuchsia, it)

// H1 = abstract heading — opens a new page (each abstract in the batch
// PDF gets its own page). Fuchsia, wraps naturally.
#let h1-seen = counter("h1-seen")
#show heading.where(level: 1): it => {
  context { if h1-seen.get().first() > 0 { pagebreak(weak: true) } }
  h1-seen.step()
  block(above: 0pt, below: 10pt)[
    #set text(font: "Avenir Next", size: 15pt, weight: 700, fill: c-fuchsia)
    #it.body
    #v(4pt, weak: true)
    #line(length: 100%, stroke: 1.4pt + c-fuchsia)
  ]
}

// H2/H3 fallback (not typically used in single abstracts but kept for
// safety when pandoc emits them).
#show heading.where(level: 2): it => block(above: 12pt, below: 6pt)[
  #set text(font: "Avenir Next", size: 11pt, weight: 700, fill: c-navy)
  #it.body
]
#show heading.where(level: 3): it => block(above: 10pt, below: 5pt)[
  #set text(font: "Avenir Next", size: 10pt, weight: 700, fill: c-teal)
  #it.body
]

// --- body -----------------------------------------------------------------
$body$
