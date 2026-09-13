#!/usr/bin/env python3
"""Build a combined NECB 2026 program book.

Takes the existing program-book.pdf (short 250-word abstract entries,
schedule, speaker cards, TOC, etc.) and, for each abstract that also
has an author-submitted one-page PDF in docs/review/build/pdfs/,
inserts that page immediately after the short abstract's text — so
each abstract in the combined book carries both the 250-word entry
AND the presenter's full one-page extended abstract, in order.

Native merge: the imported author page is scaled to half-letter to
match the book's page size and kept vector (text stays selectable,
figures stay sharp). Outline bookmarks from the program book are
preserved via PdfWriter.clone_from(); insertions are done back-to-
front so earlier insertions don't shift the target positions of the
later ones.

Usage:
    python3 scripts/build_combined_book.py           # dry render
    python3 scripts/build_combined_book.py --publish  # + static/files/
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter, PageObject, Transformation

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "review" / "build"
PDF_DIR = BUILD / "pdfs"
SOURCE = ROOT / "static" / "files" / "program-book.pdf"
OUT = BUILD / "program-book-full.pdf"
PUBLISH = ROOT / "static" / "files" / "program-book-full.pdf"

ABSTRACT_ID_RE = re.compile(r"^(A\d{3})\b")


def walk_outline(items, out):
    """Flatten a pypdf outline tree into a list of (title, item) pairs
    preserving order."""
    for item in items:
        if isinstance(item, list):
            walk_outline(item, out)
        else:
            out.append(item)


def get_abstract_page_map(reader: PdfReader) -> dict[str, int]:
    """Return {abstract_id -> 0-indexed page number in the source PDF}
    by walking the outline for H3-level entries whose titles begin with
    an abstract ID like 'A093 · …'."""
    items: list = []
    walk_outline(reader.outline, items)
    m: dict[str, int] = {}
    for item in items:
        title = str(item.title)
        match = ABSTRACT_ID_RE.match(title)
        if not match:
            continue
        page = reader.get_destination_page_number(item)
        aid = match.group(1)
        # If the outline lists the same id twice (shouldn't, but be
        # safe), keep the earliest occurrence.
        if aid not in m:
            m[aid] = page
    return m


def scale_page_to_half_letter(page):
    """Uniformly scale + center an imported PDF page onto a
    5.5 × 8.5 in half-letter canvas."""
    target_w, target_h = 396.0, 612.0
    box = page.mediabox
    src_w = float(box.width)
    src_h = float(box.height)
    if src_w == 0 or src_h == 0:
        return page
    if src_w > src_h:
        page.rotate(90)
        src_w, src_h = src_h, src_w
    scale = min(target_w / src_w, target_h / src_h)
    tx = (target_w - src_w * scale) / 2.0
    ty = (target_h - src_h * scale) / 2.0
    blank = PageObject.create_blank_page(width=target_w, height=target_h)
    op = Transformation().scale(scale, scale).translate(tx, ty)
    blank.merge_transformed_page(page, op)
    return blank


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--publish", action="store_true",
                    help="also copy to static/files/program-book-full.pdf")
    args = ap.parse_args()

    if not SOURCE.exists():
        sys.exit(f"error: {SOURCE.relative_to(ROOT)} missing — run "
                 "scripts/build_program_book.py + render_pdf.py first")

    reader = PdfReader(str(SOURCE))
    aid_start = get_abstract_page_map(reader)
    print(f"outline: {len(aid_start)} abstract entries in {SOURCE.name}")

    # Sort abstracts by their page position, then compute each
    # abstract's LAST short-text page (= next abstract's start - 1;
    # for the last abstract, = len(pages) - 1 minus the back-matter
    # pages we can detect via outline, but the simplest heuristic is
    # 'up to the next H2-or-higher heading'). Practically, using
    # 'next-abstract-start - 1' is fine; the last abstract's own last
    # page followed by Organizing Committee still lands cleanly since
    # Organizing Committee starts on its own page anyway.
    ordered = sorted(aid_start.items(), key=lambda x: x[1])
    aid_end: dict[str, int] = {}
    for i, (aid, start) in enumerate(ordered):
        if i + 1 < len(ordered):
            aid_end[aid] = ordered[i + 1][1] - 1
        else:
            aid_end[aid] = len(reader.pages) - 1  # last abstract

    # Which abstracts have an author PDF on disk?
    pdf_files = {p.stem.upper(): p
                 for p in PDF_DIR.glob("A*.pdf")}
    to_insert: list[tuple[int, Path]] = []
    for aid, end in aid_end.items():
        if aid in pdf_files:
            to_insert.append((end, pdf_files[aid]))
    print(f"inserting {len(to_insert)} extended-abstract pages")

    # Rebuild the writer from the source (preserves outline + metadata).
    writer = PdfWriter(clone_from=reader)

    # Insert back-to-front so the pre-computed 0-indexed positions
    # remain valid as insertions shift downstream page indexes.
    for end_page, pdf_path in sorted(to_insert, key=lambda x: -x[0]):
        author = PdfReader(str(pdf_path))
        for p in author.pages[:1]:  # cap at page 1
            writer.insert_page(scale_page_to_half_letter(p),
                               index=end_page + 1)

    # Preserve the two-page-right layout hint.
    writer.page_layout = "/TwoPageRight"
    writer.add_metadata({
        "/Title": "NECB 2026 · Program Book (Full)",
        "/Subject": "Program + extended abstracts, combined",
    })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "wb") as f:
        writer.write(f)
    r2 = PdfReader(str(OUT))
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(r2.pages)} pages, "
          f"{size_mb:.1f} MB)")

    if args.publish:
        PUBLISH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT, PUBLISH)
        print(f"       {PUBLISH.relative_to(ROOT)}  (published)")
        print(f"       https://newenglandcompbio.org/files/program-book-full.pdf")


if __name__ == "__main__":
    main()
