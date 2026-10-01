// X / LinkedIn banners and profile images in the Luca-logo style.
// typst compile --root ../../.. --font-path ../../../scripts/templates/fonts --input v=<variant> --ppi 72 social.typ out.png
#let fuchsia = rgb("#B31E4B"); #let navy = rgb("#1C3D7B"); #let teal = rgb("#3B7368"); #let muted = rgb("#6B6B6E")
#let v = sys.inputs.at("v")
#set text(font: "Inter")
// Logo lockup with 2026 beside the wordmark (necb ends x=324/643, baseline y=69/116).
#let lockup(w) = { let h = w * 116 / 643; box(width: w, height: h, {
  place(image("/static/img/logo/necb-horizontal.svg", width: w, height: h))
  place(dx: w * 324 / 643 + w * 0.024, dy: h * 69 / 116,
    text(weight: 800, size: w * 0.1, tracking: -0.03em, fill: fuchsia, top-edge: "baseline", bottom-edge: "baseline")[2026])
}) }
#let info(s) = stack(spacing: s * 0.55,
  text(size: s, weight: 600, fill: navy)[October 1–2, 2026 #text(fill: muted, weight: 400)[· Microsoft Research New England · Cambridge, MA]],
  text(font: "IBM Plex Mono", size: s * 0.92, weight: 500, fill: fuchsia)[newenglandcompbio.org #h(0.6em)·#h(0.6em) \@NewEngCompBio #h(0.6em)·#h(0.6em) \#NECB2026])
#if v == "x" {
  set page(width: 1500pt, height: 500pt, margin: 0pt, fill: white)
  place(image("art-x.png", width: 690pt, height: 500pt))
  place(dx: 745pt, dy: 0pt, box(height: 500pt, align(horizon, stack(spacing: 38pt, lockup(660pt), info(19pt)))))
} else if v == "linkedin" {
  set page(width: 1584pt, height: 396pt, margin: 0pt, fill: white)
  place(image("art-li.png", width: 640pt, height: 396pt))
  place(dx: 700pt, dy: 0pt, box(height: 396pt, align(horizon, stack(spacing: 30pt, lockup(700pt), info(19pt)))))
} else if v == "og" {
  // link-preview card (Open Graph / Twitter), 1200 x 630
  set page(width: 1200pt, height: 630pt, margin: 0pt, fill: white)
  place(dx: 690pt, image("art-x.png", height: 630pt))
  place(dx: 70pt, dy: 0pt, box(height: 630pt, align(horizon, stack(spacing: 34pt,
    text(font: "IBM Plex Mono", size: 18pt, weight: 500, fill: teal)[inaugural symposium · cambridge, ma],
    lockup(600pt),
    stack(spacing: 12pt,
      text(size: 24pt, weight: 600, fill: navy)[October 1–2, 2026],
      text(size: 21pt, fill: muted)[Microsoft Research New England · Cambridge, MA],
      text(font: "IBM Plex Mono", size: 19pt, weight: 500, fill: fuchsia)[newenglandcompbio.org])))))
} else {
  // square profile image; the mark sits inside the circular crop
  let s = if v == "avatar" { 400pt } else { 300pt }
  set page(width: s, height: s, margin: 0pt, fill: white)
  place(center + horizon, image("/static/img/logo/necb-mark.svg", height: s * 0.58))
}
