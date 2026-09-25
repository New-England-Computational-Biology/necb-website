#!/usr/bin/env python3
"""Compile one standalone PDF per accepted abstract.

Unlike scripts/split_abstracts.py (which extracts page ranges from the
compiled program book, so each individual PDF inherits the book's
running header, footer, and page numbering), this script:

  1. Builds a single markdown file containing every accepted abstract,
     each opened by an H1 heading so it lands on a fresh page.
  2. Renders it via scripts/render_pdf.py using the dedicated
     scripts/templates/abstract-single.typ template — clean NECB header,
     no book-wide page numbers, no leaked section context.
  3. Splits by abstract-ID outline into one PDF per abstract at
     static/files/necb-2026-abstracts/A###.pdf.
  4. For abstracts whose presenter submitted an extended one-page PDF,
     appends that page (scaled to the same half-letter frame) after the
     short entry.

Usage:
    python3 scripts/build_single_abstracts.py --publish
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter, PageObject, Transformation

# Reuse loaders + renderer from the program-book builder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_program_book import (          # type: ignore
    load_submissions, load_poster_ids, load_poster_day_map,
    load_poster_presenter_map, load_withdrawn_ids, load_yaml,
    render_abstract,
)

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "review" / "build"
MD_OUT = BUILD / "abstracts-standalone.md"
BUNDLE_PDF = BUILD / "abstracts-standalone.pdf"
TEMPLATE = ROOT / "scripts" / "templates" / "abstract-single.typ"
PDF_DIR = BUILD / "pdfs"                                    # extended pages
PUBLISH_DIR = ROOT / "static" / "files" / "necb-2026-abstracts"

ABSTRACT_ID_RE = re.compile(r"^(A\d{3})\b")


def _abstract_h1_wrapper(md_lines: list[str], aid: str, title: str) -> list[str]:
    """The abstract renderer emits an H3 (`### A093 · Title`). For the
    standalone template we want each abstract to be an H1 so it opens a
    new page. Convert the first H3 in the emitted block into an H1 and
    drop the preceding pagebreak marker (the H1 rule handles it)."""
    out = []
    heading_swapped = False
    for line in md_lines:
        if not heading_swapped and line.startswith(f"### {aid} · "):
            out.append(f"# {aid} · {title}")
            heading_swapped = True
            continue
        # Drop any leading typst pagebreak block (render_abstract emits
        # one before non-stick entries).
        out.append(line)
    return out


def build_markdown():
    program = load_yaml("program.yaml")
    subs = load_submissions()
    withdrawn = load_withdrawn_ids()
    poster_ids = load_poster_ids()
    day_map = load_poster_day_map()
    presenter_map = load_poster_presenter_map()

    # Selected talks — order by program.yaml
    talk_entries: list[tuple[str, dict, str, tuple[str, str]]] = []
    talk_seen = set()
    for day in program["days"]:
        for sess in day.get("sessions", []):
            for t in sess.get("talks") or []:
                aid = t["abstract_id"]
                # program.yaml is the source of truth for talks; don't
                # filter against withdrawals (A185 was poster-withdrawn
                # when it was promoted to a talk).
                if aid in talk_seen: continue
                talk_seen.add(aid)
                sub = subs.get(aid)
                if not sub: continue
                session_label = f"{day['label']} · {sess['time']}"
                hint = ((t.get("presenter") or "").strip(),
                        (t.get("affiliation") or "").strip())
                talk_entries.append((aid, sub, session_label, hint))

    # Posters — sorted by abstract id
    poster_entries: list[tuple[str, dict, str, tuple[str, str] | None]] = []
    for aid in sorted(set(poster_ids)):
        if aid in withdrawn or aid in talk_seen: continue
        sub = subs.get(aid)
        if not sub: continue
        day_label, time = day_map.get(aid, ("", ""))
        session_label = f"{day_label} · {time}".strip(" ·") or None
        hint = presenter_map.get(aid)
        poster_entries.append((aid, sub, session_label, hint))

    md: list[str] = []
    for aid, sub, session_label, hint in talk_entries + poster_entries:
        block = render_abstract(aid, sub, session_label,
                                presenter_hint=hint,
                                stick_to_prev=True)
        md += _abstract_h1_wrapper(block, aid, sub["title"])

    MD_OUT.write_text("\n".join(md) + "\n")
    return [aid for aid, *_ in talk_entries + poster_entries]


def render_bundle():
    """Invoke render_pdf.py to compile the bundle md → single PDF."""
    cmd = [
        sys.executable, str(ROOT / "scripts" / "render_pdf.py"),
        str(MD_OUT), "--template", str(TEMPLATE),
    ]
    subprocess.run(cmd, check=True)
    # render_pdf.py drops the PDF in the same build/ folder under the
    # md's stem — abstracts-standalone.pdf.
    default = BUILD / (MD_OUT.stem + ".pdf")
    if default != BUNDLE_PDF:
        shutil.copy2(default, BUNDLE_PDF)
    return BUNDLE_PDF


def walk_outline(items, out):
    for it in items:
        if isinstance(it, list):
            walk_outline(it, out)
        else:
            out.append(it)


def _scale_page(page):
    """Scale + rotate an imported author PDF page to fit our half-letter
    frame (5.5 × 8.5 in = 396 × 612 pt)."""
    target_w, target_h = 396.0, 612.0
    box = page.mediabox
    src_w, src_h = float(box.width), float(box.height)
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


def split_and_stitch(bundle_pdf: Path, publish: bool):
    reader = PdfReader(str(bundle_pdf))
    items: list = []
    walk_outline(reader.outline, items)
    # Ordered abstract entries with start pages
    entries = []
    for it in items:
        m = ABSTRACT_ID_RE.match(str(it.title))
        if not m: continue
        entries.append((m.group(1), reader.get_destination_page_number(it)))
    # Compute end pages
    ranges = []
    n = len(reader.pages)
    for i, (aid, start) in enumerate(entries):
        end = entries[i + 1][1] - 1 if i + 1 < len(entries) else n - 1
        ranges.append((aid, start, end))

    out_dir = BUILD / "abstracts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("A*.pdf"):
        old.unlink()

    for aid, start, end in ranges:
        writer = PdfWriter()
        for p in range(start, end + 1):
            writer.add_page(reader.pages[p])
        # Append extended one-pager if present
        ext = PDF_DIR / f"{aid}.pdf"
        if ext.exists():
            ext_reader = PdfReader(str(ext))
            for p in ext_reader.pages[:1]:
                writer.add_page(_scale_page(p))
        writer.add_metadata({
            "/Title": f"NECB 2026 · Abstract {aid}",
            "/Subject": "NECB 2026 abstract",
        })
        with open(out_dir / f"{aid}.pdf", "wb") as f:
            writer.write(f)
    print(f"wrote {len(ranges)} standalone PDFs to "
          f"{out_dir.relative_to(ROOT)}")

    if publish:
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        for old in PUBLISH_DIR.glob("A*.pdf"):
            old.unlink()
        for aid, *_ in ranges:
            shutil.copy2(out_dir / f"{aid}.pdf",
                         PUBLISH_DIR / f"{aid}.pdf")
        print(f"       {PUBLISH_DIR.relative_to(ROOT)}  (published, "
              f"{len(ranges)} files)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--publish", action="store_true",
                    help="mirror abstracts into static/files/necb-2026-abstracts/")
    args = ap.parse_args()

    ids = build_markdown()
    print(f"emitted markdown for {len(ids)} abstracts → "
          f"{MD_OUT.relative_to(ROOT)}")

    pdf = render_bundle()
    print(f"rendered bundle → {pdf.relative_to(ROOT)}  "
          f"({pdf.stat().st_size / 1024 / 1024:.1f} MB)")

    split_and_stitch(pdf, args.publish)


if __name__ == "__main__":
    main()
