#!/usr/bin/env python3
"""Render a reviewer-facing markdown doc to a print-ready PDF.

Pipeline: markdown --(pandoc)--> typst --(typst)--> PDF, using the NECB
brand template in scripts/templates/packet.typ.

Usage:
    python3 scripts/render_pdf.py                        # reviewer packet
    python3 scripts/render_pdf.py docs/review/foo.md     # any markdown file
    python3 scripts/render_pdf.py --publish              # render into static/files/
    python3 scripts/render_pdf.py --keep-typst           # keep intermediate .typ

Requires: pandoc (>= 3.x) and typst (>= 0.15). Output lands in
docs/review/build/ (gitignored — regenerate rather than commit), or in
static/files/ with --publish, which Hugo serves as
https://newenglandcompbio.org/files/<name>.pdf — that copy is committed.
Keeping every public document under /files/ means crawler rules and
link audits have a single prefix to target.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "templates" / "packet.typ"
DEFAULT_SOURCE = ROOT / "docs" / "review" / "reviewer-packet.md"
BUILD_DIR = ROOT / "docs" / "review" / "build"
PUBLISH_DIR = ROOT / "static" / "files"

# Pandoc emits equal-percentage column widths, which wastes space on narrow
# first columns (e.g. "Score"). Let the first column size to content instead.
COLUMNS_RE = re.compile(
    r"columns: \(\s*\d+(?:\.\d+)?%(?:\s*,\s*\d+(?:\.\d+)?%)*\s*,?\s*\)"
)
# Pandoc leaves cell alignment as `auto`, which inherits the centering of the
# figure wrapper. Score column centered, prose columns left, all vertically
# centered so multi-line cells line up with their score.
ALIGN_RE = re.compile(r"align: \((?:\s*auto,)+\s*\)")
# A `---` right before a part heading is redundant: the heading already
# starts a new page.
DIVIDER_BEFORE_HEADING_RE = re.compile(r"#divider\(\)\n+(?==\s)")


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"error: {tool} not found on PATH (brew install {tool})")
    return path


def retune_columns(match: re.Match[str]) -> str:
    n = match.group(0).count("%")
    return "columns: (auto, " + ", ".join(["1fr"] * (n - 1)) + ")"


def retune_align(match: re.Match[str]) -> str:
    n = match.group(0).count("auto")
    cols = ["center + horizon"] + ["left + horizon"] * (n - 1)
    return "align: (" + ", ".join(cols) + ")"


def render(source: Path, keep_typst: bool, publish: bool) -> Path:
    require("pandoc")
    require("typst")
    if not source.is_file():
        sys.exit(f"error: no such file: {source}")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if publish:
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    typ_path = BUILD_DIR / (source.stem + ".typ")
    pdf_path = (PUBLISH_DIR if publish else BUILD_DIR) / (source.stem + ".pdf")

    typst_src = subprocess.run(
        [
            "pandoc",
            "--from=markdown+autolink_bare_uris+hard_line_breaks",
            "--to=typst",
            "--standalone",
            f"--template={TEMPLATE}",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    typst_src = COLUMNS_RE.sub(retune_columns, typst_src)
    typst_src = ALIGN_RE.sub(retune_align, typst_src)
    typst_src = DIVIDER_BEFORE_HEADING_RE.sub("", typst_src)
    typ_path.write_text(typst_src)

    subprocess.run(
        ["typst", "compile", "--root", str(ROOT), str(typ_path), str(pdf_path)],
        check=True,
    )

    if not keep_typst:
        typ_path.unlink()
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", nargs="?", default=str(DEFAULT_SOURCE), type=Path,
        help="markdown file to render (default: docs/review/reviewer-packet.md)",
    )
    parser.add_argument(
        "--publish", action="store_true",
        help="write the PDF into static/files/, published under /files/ on the site",
    )
    parser.add_argument(
        "--keep-typst", action="store_true",
        help="keep the intermediate .typ file in docs/review/build/",
    )
    args = parser.parse_args()
    pdf = render(args.source.resolve(), args.keep_typst, args.publish)
    print(f"wrote {pdf.relative_to(ROOT)}")
    if args.publish:
        print(f"       https://newenglandcompbio.org/files/{pdf.name} (after deploy)")


if __name__ == "__main__":
    main()
