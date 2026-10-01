// Renders Luca's logo SVGs (static/img/logo) to PDF/PNG for print.
// typst compile --root ../../.. --input f=<name> render.typ out.{pdf,png}
#let f = sys.inputs.at("f")
#set page(width: auto, height: auto, margin: 6pt, fill: none)
#image("/static/img/logo/" + f + ".svg", height: if f.starts-with("necb-mark") { 300pt } else if f.starts-with("necb-stacked") { 400pt } else { 120pt })
