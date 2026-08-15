#!/usr/bin/env python3
"""Ingest the ISCB abstract-submission dump into review-ready CSVs.

Reads (defaults to project root):
  - NECB-2026-Submission_2026-08-15.csv  — metadata export
  - NECB2026_submissions.zip             — attached PDFs

Produces in docs/review/build/ (gitignored):
  - submissions_reviewer.csv   blinded, ready to paste into the Submissions tab
  - submissions_chair.csv      full author metadata, chair-only
  - assignments.csv            first-pass round-robin at N reviews/abstract, honoring same-institution COI
  - pdfs/A001.pdf, A002.pdf …  extracted from the zip, renamed by abstract_id
  - assignments_summary.txt    per-reviewer load + any abstracts left with < N reviews after COI filtering

Usage:
    python3 scripts/ingest_submissions.py
    python3 scripts/ingest_submissions.py --reviews-per-abstract 3
    python3 scripts/ingest_submissions.py --csv other.csv --zip other.zip
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "NECB-2026-Submission_2026-08-15.csv"
DEFAULT_ZIP = ROOT / "NECB2026_submissions.zip"
BUILD_DIR = ROOT / "docs" / "review" / "build"
PDF_DIR = BUILD_DIR / "pdfs"

# Reviewer → institution keywords for the same-institution COI check.
# Keep in sync with data/organizers.yaml → reviewers.members[*].affiliation.
# Match is case-insensitive substring against the presenting affiliation +
# the full author-with-affiliations block.
REVIEWERS: list[tuple[str, list[str]]] = [
    ("Andrew Caruso",         ["abbvie"]),
    ("Curie Cha",             ["mgh", "massachusetts general", "harvard", "broad"]),
    ("Xiwei Cheng",           ["northeastern"]),
    ("Kishalay Das",          ["yale"]),
    ("Kit Gallagher",         ["mgh", "massachusetts general", "harvard", "broad"]),
    ("Jocelyn Garcia",        ["tufts"]),
    ("Aditya Gorla",          ["ucla", "california, los angeles"]),
    ("Lei Huang",             ["mgh", "massachusetts general", "harvard", "broad"]),
    ("Benjamin Jones",        ["yale"]),
    ("Panos Ketonis",         ["yale"]),
    ("Anurendra Kumar",       ["mgh", "massachusetts general", "harvard", "stanford"]),
    ("Senbao Lu",             ["wpi", "worcester polytechnic"]),
    ("Karna Mendonca",        ["northeastern"]),
    ("Zain Patel",            ["mgh", "massachusetts general", "harvard", "broad"]),
    ("Ben Perry",             ["duke"]),
    ("Anna Sappington",       ["mit", "massachusetts institute of technology", "harvard"]),
    ("Kristen Severson",      ["microsoft"]),
    ("Ross Stewart",          ["northeastern"]),
    ("Siddharth Viswanath",   ["yale"]),
    ("Ruohan Wang",           ["brown"]),
    ("Will White",            ["tufts"]),
    ("Ke Xu",                 ["yale"]),
    ("Laura Yeoh",            ["bwh", "brigham", "boston children", "harvard"]),
    ("Yikun Zhang",           ["northeastern"]),
    ("Nanxiang (Sam) Zhao",   ["merck"]),
]

REVIEWER_INSTS = {name: kws for name, kws in REVIEWERS}


def has_coi(reviewer_kws: list[str], author_affil_text: str) -> bool:
    text = author_affil_text.lower()
    return any(kw in text for kw in reviewer_kws)


def find_pdf_map(zip_path: Path) -> dict[str, str]:
    """Map Application ID (leading digits of the filename) → filename in the zip."""
    mapping: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".pdf"):
                continue
            m = re.match(r"^(\d+)", Path(name).name)
            if m:
                mapping[m.group(1)] = name
    return mapping


def extract_pdfs(zip_path: Path, id_to_zipname: dict[str, str],
                 app_to_abstract: dict[str, str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for app_id, zipname in id_to_zipname.items():
            aid = app_to_abstract.get(app_id)
            if not aid:
                continue
            target = out_dir / f"{aid}.pdf"
            with zf.open(zipname) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def assign_round_robin(rows, reviews_per_abstract):
    """Balance-first + COI-aware assignment.

    For each abstract in order, pick the `reviews_per_abstract` reviewers with
    the lowest current load who do not have an institutional COI. If we run
    out of eligible reviewers (very rare — would need most of the roster to
    conflict), fall back to the least-loaded remaining reviewers regardless
    of COI and flag them so the chairs can reassign manually.
    """
    reviewer_names = [n for n, _ in REVIEWERS]
    load = {n: 0 for n in reviewer_names}
    tiebreak = {n: i for i, n in enumerate(reviewer_names)}

    assignments = []  # list of (abstract_id, reviewer, coi_flag)
    unfilled = []     # abstract_ids that couldn't be filled COI-clean

    for r in rows:
        affil_text = " ".join([
            r.get("Affiliation", "") or "",
            r.get("Authors with affiliations (One per line)", "") or "",
        ]).strip()

        # Eligible: sorted by (load, tiebreak) — lowest load first, then round-robin
        eligible = sorted(
            (n for n in reviewer_names
             if not has_coi(REVIEWER_INSTS[n], affil_text)),
            key=lambda n: (load[n], tiebreak[n]),
        )

        picked = eligible[:reviews_per_abstract]
        gap = reviews_per_abstract - len(picked)
        if gap > 0:
            unfilled.append(r["abstract_id"])
            fallback_pool = sorted(
                (n for n in reviewer_names if n not in picked),
                key=lambda n: (load[n], tiebreak[n]),
            )
            picked.extend(fallback_pool[:gap])

        for n in picked:
            load[n] += 1
            coi_flag = has_coi(REVIEWER_INSTS[n], affil_text)
            assignments.append((r["abstract_id"], n, coi_flag))

    return assignments, load, unfilled


def ingest(csv_path: Path, zip_path: Path, reviews_per_abstract: int) -> None:
    if not csv_path.is_file():
        sys.exit(f"error: {csv_path} not found")
    if not zip_path.is_file():
        sys.exit(f"error: {zip_path} not found")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Read submissions
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Sort by Application ID (numeric, monotonically increasing → proxy for time)
    def app_id_key(r):
        try:
            return int(r["Application ID"])
        except (KeyError, ValueError, TypeError):
            return 10 ** 9
    rows.sort(key=app_id_key)
    for i, r in enumerate(rows, start=1):
        r["abstract_id"] = f"A{i:03d}"

    app_to_abstract = {r["Application ID"]: r["abstract_id"] for r in rows}

    id_to_zipname = find_pdf_map(zip_path)
    n_pdfs = sum(1 for r in rows if r["Application ID"] in id_to_zipname)

    extract_pdfs(zip_path, id_to_zipname, app_to_abstract, PDF_DIR)

    # Reviewer-facing (blinded)
    reviewer_csv = BUILD_DIR / "submissions_reviewer.csv"
    with reviewer_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "abstract_id", "title", "presenting_affiliation",
            "abstract_text", "pdf_link", "topic_keywords", "chair_notes",
        ])
        for r in rows:
            has_pdf = r["Application ID"] in id_to_zipname
            pdf_link = f"pdfs/{r['abstract_id']}.pdf" if has_pdf else ""
            w.writerow([
                r["abstract_id"],
                r.get("Title", "").strip(),
                "",  # affiliation intentionally masked for blinded review
                r.get("Abstract", "").strip(),
                pdf_link,
                "",
                "" if has_pdf else "NO_PDF · poster-only",
            ])

    # Chair-only (full metadata)
    chair_csv = BUILD_DIR / "submissions_chair.csv"
    with chair_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "abstract_id", "application_id", "presenting_name",
            "presenting_email", "presenting_affiliation",
            "authors_with_affiliations", "type_of_presentation",
            "has_pdf", "title",
        ])
        for r in rows:
            has_pdf = r["Application ID"] in id_to_zipname
            w.writerow([
                r["abstract_id"],
                r["Application ID"],
                r.get("Name", "").strip(),
                r.get("Email", "").strip(),
                r.get("Affiliation", "").strip(),
                r.get("Authors with affiliations (One per line)", "").strip(),
                r.get("Type of Presentation", "").strip(),
                "YES" if has_pdf else "NO",
                r.get("Title", "").strip(),
            ])

    # Assignments
    assignments, load, unfilled = assign_round_robin(rows, reviews_per_abstract)
    assign_csv = BUILD_DIR / "assignments.csv"
    with assign_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["abstract_id", "reviewer", "coi_flag"])
        for aid, rn, coi in assignments:
            w.writerow([aid, rn, "TRUE" if coi else "FALSE"])

    # Summary text file for the chairs
    summary_path = BUILD_DIR / "assignments_summary.txt"
    lines = [
        f"submissions:          {len(rows)}",
        f"pdfs matched:         {n_pdfs} ({n_pdfs*100//max(len(rows),1)}%)",
        f"reviews per abstract: {reviews_per_abstract}",
        f"total review slots:   {len(rows) * reviews_per_abstract}",
        f"reviewers:            {len(REVIEWERS)}",
        f"target load / reviewer: ~{len(rows) * reviews_per_abstract // len(REVIEWERS)}",
        "",
        "load per reviewer (should cluster tightly around the target):",
    ]
    for n, _ in REVIEWERS:
        lines.append(f"  {load[n]:>3}  {n}")
    if unfilled:
        lines.append("")
        lines.append(f"⚠  couldn't fill COI-clean for {len(unfilled)} abstract(s):")
        for aid in unfilled:
            lines.append(f"    {aid}")
        lines.append("   review manually and reassign in the sheet.")
    summary_path.write_text("\n".join(lines) + "\n")

    # Print summary
    print(f"submissions:        {len(rows)}")
    print(f"pdfs matched:       {n_pdfs} ({n_pdfs*100//max(len(rows),1)}%)")
    print(f"reviewer view:      {reviewer_csv.relative_to(ROOT)}")
    print(f"chair view:         {chair_csv.relative_to(ROOT)}")
    print(f"assignments:        {assign_csv.relative_to(ROOT)}")
    print(f"summary:            {summary_path.relative_to(ROOT)}")
    print(f"pdfs extracted to:  {PDF_DIR.relative_to(ROOT)}/  ({n_pdfs} files)")
    print()
    print("load per reviewer:")
    for n, _ in REVIEWERS:
        print(f"  {load[n]:>3}  {n}")
    if unfilled:
        print()
        print(f"⚠  {len(unfilled)} abstract(s) couldn't be filled COI-clean — see summary.txt")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                   help=f"default: {DEFAULT_CSV.name}")
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP,
                   help=f"default: {DEFAULT_ZIP.name}")
    p.add_argument("--reviews-per-abstract", type=int, default=2)
    args = p.parse_args()
    ingest(args.csv, args.zip, args.reviews_per_abstract)


if __name__ == "__main__":
    main()
