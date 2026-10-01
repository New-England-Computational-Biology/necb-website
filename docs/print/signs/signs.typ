// Day-of table signs (US Letter landscape) in the new logo style.
// typst compile --root ../../.. --font-path ../../../scripts/templates/fonts signs.typ ../build/necb-2026-day-of-signs.pdf
#let fuchsia = rgb("#B31E4B"); #let navy = rgb("#1C3D7B"); #let teal = rgb("#3B7368"); #let muted = rgb("#6B6B6E"); #let rule = rgb("#E5E7EB")
#set page(paper: "us-letter", flipped: true, margin: (x: 0.7in, y: 0.6in), fill: white)
#set text(font: "Inter", fill: navy)
#set par(spacing: 0pt, leading: 0.3em)

#let lockup(w) = { let h = w * 116 / 643; box(width: w, height: h, {
  place(image("/static/img/logo/necb-horizontal.svg", width: w, height: h))
  place(dx: w * 324 / 643 + w * 0.024, dy: h * 69 / 116,
    text(weight: 800, size: w * 0.1, tracking: -0.03em, fill: fuchsia, top-edge: "baseline", bottom-edge: "baseline")[2026])
}) }

// One sign: eyebrow, big title (shrunk to fit one line), subtitle, optional note.
#let sign(eyebrow, title, sub, note: none, size: 150pt) = page(context {
  let w = page.width - 1.4in
  let tw = measure(text(size: size, weight: 800, tracking: -0.03em)[#title]).width
  let ts = if tw > w { size * (w / tw) } else { size }
  block(height: 100%, {
    lockup(3.1in)
    v(1fr)
    text(font: "IBM Plex Mono", size: 24pt, weight: 500, fill: teal)[#lower(eyebrow)]
    v(30pt)
    text(size: ts, weight: 800, tracking: -0.03em, fill: navy)[#title]
    v(38pt)
    text(size: 34pt, weight: 600, fill: fuchsia)[#sub]
    if note != none { v(20pt); block(width: 80%, text(size: 20pt, fill: muted)[#note]) }
    v(1fr)
    line(length: 100%, stroke: 1pt + rule)
    v(8pt)
    grid(columns: (1fr, auto),
      text(font: "IBM Plex Mono", size: 13pt, fill: muted)[newenglandcompbio.org · \#NECB2026],
      text(font: "IBM Plex Mono", size: 13pt, fill: muted)[necb 2026 · october 1–2])
  })
})

// --- Badge pickup (balanced on the 362 attending registrants)
#sign("Badge pickup", [A – H], [Last names A to H])
#sign("Badge pickup", [I – O], [Last names I to O])
#sign("Badge pickup", [P – Z], [Last names P to Z])

// --- Food & drinks
#sign("Coffee break · 10:45 AM", [Coffee & tea], [Help yourself], size: 120pt)
#sign("Lunch · 12:15 PM", [Lunch], [One boxed lunch per person, please], size: 120pt)
#sign("Lunch · 12:15 PM", [Vegetarian], [Vegetarian boxed lunches], size: 120pt)
#sign("Lunch", [Dietary needs], [Gluten-free · vegan · allergies], note: [If you listed a dietary requirement at registration, please pick up here.], size: 120pt)
#sign("All day", [Water], [Stay hydrated], size: 120pt)
#sign("Thursday evening · 6:00 PM", [Refreshments], [MIT FutureFest Salon], size: 120pt)
