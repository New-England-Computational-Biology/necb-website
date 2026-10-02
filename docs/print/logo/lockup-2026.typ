// Luca's horizontal logo with "2026" beside the wordmark (for certificates, badges, slides).
// typst compile --root ../../.. --font-path ../../../scripts/templates/fonts lockup-2026.typ necb-2026-horizontal.{pdf,png}
#let fuchsia = rgb("#B31E4B")
#set page(width: auto, height: auto, margin: 8pt, fill: none)
#let w = 643pt
#let h = w * 116 / 643
#box(width: w, height: h, {
  place(image("/static/img/logo/necb-horizontal.svg", width: w, height: h))
  place(dx: w * 324 / 643 + w * 0.024, dy: h * 69 / 116,
    text(font: "Inter", weight: 800, size: w * 0.1, tracking: -0.03em, fill: fuchsia, top-edge: "baseline", bottom-edge: "baseline")[2026])
})
