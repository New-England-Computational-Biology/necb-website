#!/usr/bin/env python3
"""Build an 'Extended Abstracts' companion PDF for NECB 2026.

For each abstract that has an author-submitted PDF in
docs/review/build/pdfs/<abstract_id>.pdf, emit:

    <cover sheet, program-book branded, 1 page>
    <native PDF pages, no rasterization>

then concatenate the whole thing into static/files/extended-abstracts.pdf.

Cover sheets are rendered via the program-book typst template so
brand + page size (half-letter) match. Author PDFs are inserted
native — text stays selectable, figures stay sharp, fonts stay
whatever the author submitted them with.

Usage:
    python3 scripts/build_extended_abstracts.py           # dry render (build/)
    python3 scripts/build_extended_abstracts.py --publish  # + static/files/
"""

from __future__ import annotations

import argparse
import csv
import sys
import subprocess
import shutil
import re
from pathlib import Path

import yaml
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "docs" / "review" / "build"
PDF_DIR = BUILD / "pdfs"
COVERS_MD = BUILD / "extended-abstracts-covers.md"
COVERS_PDF = BUILD / "extended-abstracts-covers.pdf"
FINAL = BUILD / "extended-abstracts.pdf"
PUBLISH = ROOT / "static" / "files" / "extended-abstracts.pdf"
TEMPLATE = ROOT / "scripts" / "templates" / "program-book.typ"

CSV_REG = BUILD / "submissions_paste.csv"
CSV_LATE = BUILD / "submissions_paste_late.csv"
POSTER_SESSIONS = DATA / "posterSessions.yaml"
WITHDRAWALS = BUILD / "withdrawals.csv"


def load_program() -> dict:
    with open(DATA / "program.yaml") as f:
        return yaml.safe_load(f)


def load_submissions() -> dict[str, dict]:
    subs: dict[str, dict] = {}
    for path in (CSV_REG, CSV_LATE):
        if not path.exists():
            continue
        with open(path) as f:
            for row in csv.reader(f):
                if len(row) < 8 or not row[0].strip().startswith("A"):
                    continue
                aid = row[0].strip()
                subs[aid] = {
                    "title": " ".join(row[1].replace("\\n", " ").split()),
                    "affiliation": " ".join(row[3].split()),
                }
    return subs


def load_withdrawals() -> set[str]:
    """Return abstract IDs that should not appear."""
    if not WITHDRAWALS.exists():
        return set()
    ids: set[str] = set()
    with open(WITHDRAWALS) as f:
        for i, row in enumerate(csv.reader(f)):
            if i == 0 or not row:
                continue
            aid = row[0].strip()
            if aid.startswith("A"):
                ids.add(aid)
    return ids


def load_poster_presenters() -> dict[str, tuple[str, str, str]]:
    """Map abstract_id -> (presenter, affiliation, day_label)."""
    if not POSTER_SESSIONS.exists():
        return {}
    y = yaml.safe_load(POSTER_SESSIONS.read_text())
    m: dict[str, tuple[str, str, str]] = {}
    for day in y.get("days", []):
        for p in day.get("posters", []):
            aid = p.get("abstract_id", "").strip()
            if aid:
                m[aid] = (
                    (p.get("presenter") or "").strip(),
                    (p.get("affiliation") or "").strip(),
                    day.get("label", ""),
                )
    return m


def load_talk_presenters(program) -> dict[str, tuple[str, str, str]]:
    m: dict[str, tuple[str, str, str]] = {}
    for day in program["days"]:
        for sess in day["sessions"]:
            for t in (sess.get("talks") or []):
                aid = t.get("abstract_id", "").strip()
                if aid:
                    m[aid] = (
                        (t.get("presenter") or "").strip(),
                        (t.get("affiliation") or "").strip(),
                        f"{day['label']} · {sess.get('time','')}",
                    )
    return m


def _typ(s: str) -> str:
    """Escape for typst content block."""
    return (s.replace("\\", "\\\\")
             .replace("[", "\\[").replace("]", "\\]")
             .replace("#", "\\#").replace("@", "\\@")
             .replace("<", "\\<").replace(">", "\\>"))


def render_covers(entries: list[dict]) -> None:
    """Write a markdown driver that produces one cover page per abstract.

    Each cover is a typst raw block: fuchsia 'EXTENDED ABSTRACT' eyebrow,
    monospace abstract-ID, bold navy title, teal presenter · affiliation,
    small italic session note. A weak pagebreak between each so every
    cover fills exactly one page.
    """
    lines: list[str] = []
    # Front-matter title page — matches the program book's cover style.
    lines += [
        "```{=typst}",
        "#v(1.4in)",
        "#align(left)[",
        "  #block[",
        "    #box(fill: c-fuchsia, radius: 999pt, width: 0.35em, "
        "height: 0.35em, [])",
        "    #h(0.4em)",
        "    #text(font: \"Avenir Next\", size: 9pt, weight: 600, "
        "fill: c-teal, tracking: 1pt)[",
        "      #upper[Inaugural Symposium · Cambridge, MA]",
        "    ]",
        "  ]",
        "  #v(10pt)",
        "  #text(font: \"Avenir Next\", size: 38pt, weight: 700, fill: c-fuchsia)[",
        "    NECB 2026 \\",
        "    #text(size: 32pt, fill: c-navy)[Extended Abstracts]",
        "  ]",
        "  #v(14pt)",
        "  #text(font: \"Avenir Next\", size: 11pt, weight: 600, fill: c-navy)[",
        "    October 1–2, 2026",
        "  ]",
        "  #text(font: \"Avenir Next\", size: 11pt, fill: c-muted)[",
        "    #h(0.3em) · #h(0.3em) Microsoft Research New England",
        "  ]",
        "  #v(20pt)",
        "  #block(width: 4in)[",
        "    #set text(font: \"Charter\", size: 10.5pt, fill: c-ink)",
        "    #set par(leading: 0.6em, justify: false)",
        "    Companion to the NECB 2026 program book. One page per "
        "accepted talk and poster, exactly as the presenter submitted "
        "it — with a short cover sheet in front of each.",
        "  ]",
        "]",
        "```",
        "",
    ]

    for e in entries:
        lines += [
            "```{=typst}",
            "#pagebreak(weak: true)",
            "#v(1.2in)",
            "#block[",
            "  #text(font: \"Avenir Next\", size: 8pt, weight: 600, "
            "fill: c-teal, tracking: 1.5pt)[",
            "    #upper[Extended Abstract]",
            "  ]",
            "  #v(6pt)",
            "  #text(font: \"Menlo\", size: 14pt, weight: 700, fill: c-fuchsia)[",
            f"    {_typ(e['aid'])}",
            "  ]",
            "  #v(10pt)",
            "  #text(font: \"Avenir Next\", size: 16pt, weight: 700, fill: c-navy)[",
            f"    {_typ(e['title'])}",
            "  ]",
            "  #v(14pt)",
            "  #text(font: \"Avenir Next\", size: 11pt, fill: c-ink)[",
            f"    {_typ(e['presenter'])}",
            "  ]",
            "  #v(3pt)",
            "  #text(font: \"Avenir Next\", size: 10pt, fill: c-teal)[",
            f"    {_typ(e['affiliation'])}",
            "  ]",
            "  #v(18pt)",
            "  #line(length: 30%, stroke: 0.6pt + c-rule)",
            "  #v(10pt)",
            "  #text(font: \"Avenir Next\", size: 9pt, fill: c-muted, "
            "style: \"italic\")[",
            f"    {_typ(e['session'])}",
            "  ]",
            "]",
            "```",
            "",
        ]
    COVERS_MD.write_text("\n".join(lines) + "\n")


def compile_covers() -> Path:
    """Compile covers.md via the same pandoc → typst pipeline. Returns
    the resulting PDF path."""
    # Reuse the render script's approach: pandoc → typst → typst compile.
    typst_src = subprocess.run(
        [
            "pandoc",
            "--from=markdown+autolink_bare_uris+hard_line_breaks",
            "--to=typst",
            "--standalone",
            f"--template={TEMPLATE}",
            str(COVERS_MD),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    typ_path = BUILD / "extended-abstracts-covers.typ"
    typ_path.write_text(typst_src)
    subprocess.run(
        ["typst", "compile", "--root", str(ROOT),
         str(typ_path), str(COVERS_PDF)],
        check=True,
    )
    typ_path.unlink()
    return COVERS_PDF


def _scale_page_to_half_letter(page):
    """Uniformly scale + center an imported PDF page onto a 5.5 × 8.5 in
    half-letter canvas, matching the cover sheet page size. Preserves
    aspect ratio; text stays native, no rasterization."""
    from pypdf import Transformation, PageObject
    from pypdf.generic import RectangleObject
    target_w, target_h = 396.0, 612.0  # 5.5 × 8.5 in @ 72 dpi

    box = page.mediabox
    src_w = float(box.width)
    src_h = float(box.height)
    if src_w == 0 or src_h == 0:
        return page

    # Rotate 90° first if the source page is landscape but our target
    # is portrait — otherwise long rows of text end up sideways.
    landscape_src = src_w > src_h
    if landscape_src:
        page.rotate(90)
        src_w, src_h = src_h, src_w  # after rotation

    scale = min(target_w / src_w, target_h / src_h)
    # Translate so the scaled content is centered on the target page.
    tx = (target_w - src_w * scale) / 2.0
    ty = (target_h - src_h * scale) / 2.0

    # Start from a blank half-letter canvas so the mediabox is exactly
    # our target size, then merge the scaled/translated source onto it.
    blank = PageObject.create_blank_page(width=target_w, height=target_h)
    op = Transformation().scale(scale, scale).translate(tx, ty)
    blank.merge_transformed_page(page, op)
    return blank


def interleave(entries: list[dict]) -> None:
    """Read covers.pdf + each author PDF and interleave. covers.pdf has
    N+1 pages: a title page followed by N cover pages (one per abstract,
    in the same order as `entries`). Author pages are scaled to
    half-letter so page size stays consistent with the cover sheets.
    """
    covers = PdfReader(str(COVERS_PDF))
    writer = PdfWriter()
    # Title page
    writer.add_page(covers.pages[0])
    for i, e in enumerate(entries):
        # Cover sheet for this abstract
        writer.add_page(covers.pages[i + 1])
        # Author PDF pages — scaled to half-letter. Cap at page 1 only:
        # the extended-abstract call is for a single-page submission,
        # anything longer is overflow (A040, A182, A185) that we don't
        # want mixed into the companion.
        author = PdfReader(str(e["pdf_path"]))
        for page in author.pages[:1]:
            writer.add_page(_scale_page_to_half_letter(page))
    # Set /PageLayout /TwoPageRight to match the program book.
    writer.page_layout = "/TwoPageRight"
    writer.add_metadata({
        "/Title": "NECB 2026 · Extended Abstracts",
        "/Subject": "Companion volume to the NECB 2026 program book",
    })
    with open(FINAL, "wb") as f:
        writer.write(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--publish", action="store_true",
                    help="also copy to static/files/extended-abstracts.pdf")
    args = ap.parse_args()

    if not shutil.which("pandoc") or not shutil.which("typst"):
        sys.exit("error: pandoc + typst required on PATH")

    program = load_program()
    subs = load_submissions()
    withdrawn = load_withdrawals()
    talks = load_talk_presenters(program)
    posters = load_poster_presenters()

    # Collect (aid, sub, pdf_path) triples: every AID with a local PDF
    # and a known presenter (talk or poster), excluding withdrawn.
    pdf_files = {p.stem.upper(): p for p in PDF_DIR.glob("A*.pdf")}
    entries: list[dict] = []
    for aid in sorted(pdf_files):
        if aid in withdrawn:
            continue
        if aid in talks:
            presenter, affil, session_label = talks[aid]
            kind = "Selected talk"
        elif aid in posters:
            presenter, affil, session_label = posters[aid]
            kind = "Selected poster"
        else:
            continue
        sub = subs.get(aid, {})
        title = sub.get("title") or "(title TBD)"
        affil = affil or sub.get("affiliation") or ""
        entries.append({
            "aid": aid,
            "title": title,
            "presenter": presenter,
            "affiliation": affil,
            "session": f"{kind} · {session_label}",
            "pdf_path": pdf_files[aid],
        })

    print(f"assembling {len(entries)} extended abstracts")

    render_covers(entries)
    compile_covers()
    interleave(entries)

    reader = PdfReader(str(FINAL))
    print(f"wrote {FINAL.relative_to(ROOT)}  ({len(reader.pages)} pages, "
          f"{FINAL.stat().st_size/1024/1024:.1f} MB)")

    if args.publish:
        PUBLISH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FINAL, PUBLISH)
        print(f"       {PUBLISH.relative_to(ROOT)}  (published)")
        print(f"       https://newenglandcompbio.org/files/extended-abstracts.pdf")


if __name__ == "__main__":
    main()
