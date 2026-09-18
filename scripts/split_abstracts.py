#!/usr/bin/env python3
"""Split necb-2026-program-book.pdf into one PDF per abstract.

Reads the compiled program book's outline for H3-level entries whose
titles begin with an abstract ID (e.g. "A093 · FlowMap: ..."), then
extracts each abstract's page range as a standalone PDF at
static/files/abstracts/A###.pdf. Also copies the same PDF into
docs/review/build/abstracts/ as a working directory for iteration.

Downstream: the site templates link each abstract ID to
/files/abstracts/A###.pdf so readers can share a single-abstract link
without downloading the 50 MB program book.

Usage:
    python3 scripts/split_abstracts.py            # dry run, no publish
    python3 scripts/split_abstracts.py --publish  # + static/files/abstracts/
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "review" / "build" / "abstracts"
SOURCE = ROOT / "static" / "files" / "necb-2026-program-book.pdf"
# Edition-specific published path so future NECB editions get their own
# stable per-abstract URL space and old links stay valid indefinitely.
PUBLISH_DIR = ROOT / "static" / "files" / "necb-2026-abstracts"

ABSTRACT_ID_RE = re.compile(r"^(A\d{3})\b")


def walk_outline(items, out):
    """Flatten pypdf outline (which is a nested list) into a single
    list preserving order."""
    for item in items:
        if isinstance(item, list):
            walk_outline(item, out)
        else:
            out.append(item)


def get_abstract_ranges(reader):
    """Return an ordered list of (abstract_id, start_page, end_page)
    tuples, where pages are 0-indexed and end is INCLUSIVE.

    end_page is the page just before the next abstract's start, or the
    last page of the book for the tail entry (we cap the tail at
    reasonable length so it doesn't swallow the back matter — using
    'next abstract's start − 1' handles everything but the final one,
    for which we use the last page of the source or the next non-A H1)."""
    items: list = []
    walk_outline(reader.outline, items)

    # First pass: collect abstract entries and every H1/H2 for boundary
    # detection of the very last abstract.
    entries = []
    for item in items:
        title = str(item.title)
        m = ABSTRACT_ID_RE.match(title)
        page = reader.get_destination_page_number(item)
        entries.append((title, page, bool(m)))

    ranges = []
    n_pages = len(reader.pages)
    for i, (title, page, is_abstract) in enumerate(entries):
        if not is_abstract:
            continue
        m = ABSTRACT_ID_RE.match(title)
        aid = m.group(1)
        # Find the next entry (abstract OR non-abstract H1) that starts
        # after this one — its start page − 1 is our end.
        end = n_pages - 1
        for j in range(i + 1, len(entries)):
            _, next_page, _ = entries[j]
            if next_page > page:
                end = next_page - 1
                break
        ranges.append((aid, page, end))
    return ranges


def extract_range(reader, start, end, aid):
    """Extract pages [start..end] (0-indexed, inclusive) into a fresh
    single-abstract PdfWriter. Metadata is minimal — title = A###."""
    writer = PdfWriter()
    for p in range(start, end + 1):
        writer.add_page(reader.pages[p])
    writer.add_metadata({
        "/Title": f"NECB 2026 · Abstract {aid}",
        "/Subject": "NECB 2026 abstract",
    })
    return writer


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", action="store_true",
                    help="mirror abstracts into static/files/abstracts/")
    args = ap.parse_args()

    if not SOURCE.exists():
        sys.exit(f"error: {SOURCE.relative_to(ROOT)} missing — build the "
                 "program book first "
                 "(scripts/build_program_book.py + render_pdf.py + "
                 "build_combined_book.py)")

    reader = PdfReader(str(SOURCE))
    ranges = get_abstract_ranges(reader)
    print(f"outline: {len(ranges)} abstracts in {SOURCE.name}")

    BUILD.mkdir(parents=True, exist_ok=True)
    # Clear stale abstract files from a previous run so we don't leave
    # dangling PDFs for withdrawn abstracts.
    for old in BUILD.glob("A*.pdf"):
        old.unlink()

    max_pages = 0
    for aid, start, end in ranges:
        writer = extract_range(reader, start, end, aid)
        out_path = BUILD / f"{aid}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        max_pages = max(max_pages, end - start + 1)

    total = sum((BUILD / f"{aid}.pdf").stat().st_size
                for aid, *_ in ranges) / 1024 / 1024
    print(f"wrote {len(ranges)} PDFs to {BUILD.relative_to(ROOT)}  "
          f"(total {total:.1f} MB, max {max_pages} pages / abstract)")

    if args.publish:
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        for old in PUBLISH_DIR.glob("A*.pdf"):
            old.unlink()
        for aid, *_ in ranges:
            shutil.copy2(BUILD / f"{aid}.pdf", PUBLISH_DIR / f"{aid}.pdf")
        print(f"       {PUBLISH_DIR.relative_to(ROOT)}  (published, "
              f"{len(ranges)} files)")


if __name__ == "__main__":
    main()
