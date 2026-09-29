// NECB 2026 logo lockups. Mark: six nodes (the six New England states) linked through a hub.
// Build: typst compile --font-path ../banners/fonts --input v=<variant> lockups.typ out.{pdf,svg,png}
#let fuchsia = rgb("#B3174D"); #let navy = rgb("#273D91"); #let teal = rgb("#0F5A57"); #let gold = rgb("#D58A19")
#let variant = sys.inputs.at("v", default: "horizontal")
#set page(width: auto, height: auto, margin: 6pt, fill: none)
#set text(font: "Arimo", weight: 700)

// The mark, drawn natively (120-unit grid, scaled to `size`) so SVG output has no nested images.
#let mark(size: 90pt, mono: none) = {
  let u = size / 120
  let c(col) = if mono == none { col } else { mono }
  let halo = if mono == none { white } else { none }
  let ring = if mono == none { navy.transparentize(70%) } else { mono.transparentize(55%) }
  let V = range(6).map(i => { let a = -90deg + i * 60deg; (60 + 44 * calc.cos(a), 60 + 44 * calc.sin(a)) })
  let seg(p, q, col, w) = place(line(start: (p.at(0) * u, p.at(1) * u), end: (q.at(0) * u, q.at(1) * u), stroke: (paint: col, thickness: w * u, cap: "round")))
  let dot(p, r, col) = place(dx: (p.at(0) - r) * u, dy: (p.at(1) - r) * u,
    circle(radius: r * u, fill: col, stroke: if halo == none { none } else { 2.5 * u + halo }))
  box(width: size, height: size, {
    for i in range(6) { seg(V.at(i), V.at(calc.rem(i + 1, 6)), ring, 4) }
    for i in (0, 2, 4) { seg(V.at(i), (60, 60), c(fuchsia), 5.5) }
    for (i, col) in (gold, navy, teal, gold, navy, teal).enumerate() { dot(V.at(i), 9, c(col)) }
    dot((60, 60), 12, c(fuchsia))
  })
}
#let wm(c1: fuchsia, c2: navy, size: 54pt) = [#text(size: size, fill: c1, tracking: -1pt)[NECB]#h(size * 0.15)#text(size: size, fill: c2, tracking: -1pt)[2026]]
#let tag(c: teal, size: 9.5pt, dx: 0pt, trk: 1pt) = move(dx: dx, text(size: size, fill: c, tracking: trk)[NEW ENGLAND COMPUTATIONAL BIOLOGY])
// Tagline offsets/tracking fitted so it spans exactly the width of "NECB 2026".
#let H = (dx: 3.00pt, trk: 2.123pt)
#let S = (dx: 0.48pt, trk: 1.828pt)

#if variant == "horizontal" {
  grid(columns: 2, column-gutter: 14pt, align: horizon, mark(), stack(spacing: 8pt, wm(), tag(..H)))
} else if variant == "horizontal-white" {
  grid(columns: 2, column-gutter: 14pt, align: horizon, mark(mono: white), stack(spacing: 8pt, wm(c1: white, c2: white), tag(c: white, ..H)))
} else if variant == "stacked" {
  align(center, stack(spacing: 10pt, mark(size: 110pt), wm(size: 48pt), tag(size: 8.5pt, ..S)))
} else if variant == "mark" {
  mark(size: 120pt)
} else if variant == "mark-white" {
  mark(size: 120pt, mono: white)
}
