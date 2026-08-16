#!/usr/bin/env python3
"""Ingest the ISCB abstract-submission dump into review-ready CSVs.

Reads (defaults to project root):
  - NECB-2026-Submission_2026-08-15.csv  — metadata export
  - NECB2026_submissions.zip             — attached PDFs
  - docs/review/build/reviewer_topics.yaml  — per-reviewer topic keywords (topic-aware mode only)

Produces in docs/review/build/ (gitignored):
  - submissions_reviewer.csv   blinded, ready to paste into the Submissions tab
  - submissions_chair.csv      full author metadata, chair-only
  - assignments.csv            balanced + COI-aware + optional topic affinity
  - pdfs/A001.pdf, A002.pdf …  extracted from the zip, renamed by abstract_id
  - assignments_summary.txt    per-reviewer load + affinity stats + unfilled abstracts

Usage:
    python3 scripts/ingest_submissions.py
    python3 scripts/ingest_submissions.py --reviews-per-abstract 3
    python3 scripts/ingest_submissions.py --no-topic-aware        # pure round-robin
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

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "NECB-2026-Submission_2026-08-15.csv"
DEFAULT_ZIP = ROOT / "NECB2026_submissions.zip"
BUILD_DIR = ROOT / "docs" / "review" / "build"
PDF_DIR = BUILD_DIR / "pdfs"
TOPICS_YAML = BUILD_DIR / "reviewer_topics.yaml"

# Reviewer → institution keywords for the same-institution COI check.
# Keep in sync with data/organizers.yaml → reviewers.members[*].affiliation.
# Match is case-insensitive substring against the presenting affiliation +
# the full author-with-affiliations block.
REVIEWERS: list[tuple[str, list[str]]] = [
    ("Ritwik Anand",          ["northeastern"]),
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


# Tokens dropped when tokenizing multi-word topic phrases into unigrams.
# These match everywhere and would dilute the affinity signal.
_STOPWORDS = frozenset({
    "for", "of", "the", "and", "in", "on", "to", "with", "from", "into",
    "onto", "at", "by", "as", "or", "a", "an", "this", "these", "those",
    "learning", "models", "model", "modeling", "biology", "computational",
    "machine", "deep", "based", "analysis", "methods", "data", "high",
    "large", "small", "novel", "approach", "framework", "system", "tools",
    "using", "via", "across",
})

# Bidirectional synonym / acronym groups. If a reviewer's topic contains any
# item in a row (as a substring), the other items in the row are added to their
# match set. Keep entries lowercase; matches are case-insensitive.
_SYNONYMS: list[list[str]] = [
    ["single-cell genomics", "scrna-seq", "single-cell rna-seq", "single cell"],
    ["single-cell transcriptomics", "scrna-seq", "single-cell rna-seq"],
    ["spatial transcriptomics", "merfish", "visium", "xenium", "spatial omics", "seqfish"],
    ["transcription factor binding", "tf binding", "motif discovery", "chip-seq"],
    ["chromatin accessibility", "atac-seq", "scatac-seq"],
    ["single-cell atac-seq", "scatac-seq", "atac-seq"],
    ["protein language model", "plm", "esm", "esm-2", "esm-3"],
    ["graph neural network", "gnn", "gnns", "message passing"],
    ["large language model", "llm", "llms", "gpt"],
    ["genome-wide association", "gwas"],
    ["polygenic risk", "prs", "polygenic score"],
    ["protein-protein interaction", "ppi", "ppis", "interactome"],
    ["protein structure prediction", "alphafold", "af2", "af3", "boltz", "esmfold"],
    ["diffusion model", "denoising diffusion", "score-based"],
    ["cancer evolution", "tumor evolution", "clonal evolution", "phylogeny"],
    ["clonal dynamics", "subclonal", "clonal evolution"],
    ["electronic health record", "ehr", "ehrs", "clinical notes"],
    ["mass spectrometry", "lc-ms", "proteomics"],
    ["rna sequencing", "rna-seq", "bulk rna-seq"],
    ["crispr screen", "perturb-seq", "crispr screens"],
    ["variant interpretation", "missense variant", "vus"],
    ["regulatory genomics", "cis-regulatory", "enhancer", "regulatory element"],
    ["generative models", "generative model", "generative ai"],
    ["geometric deep learning", "manifold", "riemannian"],
    ["adaptive therapy", "evolutionary therapy", "resistance evolution"],
    ["drug discovery", "drug design", "hit discovery", "lead optimization"],
    ["drug design", "structure-based drug design", "molecular design"],
    ["cell-cell communication", "cell-cell interaction", "ligand-receptor"],
    ["tumor microenvironment", "tme", "immune microenvironment"],
    ["computational pathology", "digital pathology", "whole-slide image", "wsi"],
    ["whole-genome sequencing", "wgs", "whole genome"],
]


def _tokenize_phrase(phrase: str) -> list[str]:
    """Split a topic phrase into content unigrams (drop stopwords, short/numeric)."""
    parts = re.split(r"[\s/,]+", phrase.replace("-", " ").lower())
    return [p for p in parts if p and len(p) >= 5 and p not in _STOPWORDS and not p.isdigit()]


def _expand_topics(topics: list[str]) -> set[str]:
    """Given raw reviewer topic phrases, build the full match-token set:
       - original phrase (lowercased)
       - each content unigram (len ≥ 5, non-stopword)
       - synonyms / acronyms from any group the phrase touches
    Returned as a set — each token contributes at most once to affinity.
    """
    tokens: set[str] = set()
    topics_lc = [t.lower().strip() for t in topics if t and t.strip()]
    for phrase in topics_lc:
        tokens.add(phrase)
        tokens.update(_tokenize_phrase(phrase))
        for group in _SYNONYMS:
            group_lc = [g.lower() for g in group]
            if any(g in phrase or phrase in g for g in group_lc):
                tokens.update(group_lc)
    # Drop tokens shorter than 3 chars just in case a stopword slipped through.
    return {t for t in tokens if len(t) >= 3}


def load_reviewer_topics(path: Path) -> dict[str, set[str]]:
    """Read reviewer_topics.yaml → {reviewer_name: {match_token, ...}}.

    Each reviewer's raw topic phrases are expanded via `_expand_topics`:
    original phrases + content unigrams + synonym/acronym expansions. Match is
    case-insensitive substring against title + abstract text.
    """
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    out: dict[str, set[str]] = {}
    for entry in data:
        name = entry.get("name", "").strip()
        topics = entry.get("topics") or []
        out[name] = _expand_topics([str(t) for t in topics])
    return out


def load_reviewer_labs(path: Path) -> dict[str, str]:
    """Read reviewer_topics.yaml → {reviewer_name: normalized_lab_id or None}.

    We extract just the PI's "Firstname Lastname" from lab_or_pi (dropping any
    trailing parenthetical or institution list) so labmates share the same key.
    Reviewers with lab_or_pi='unknown' or missing get None → no diversity
    constraint applies to them.
    """
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    out: dict[str, str] = {}
    for entry in data:
        name = entry.get("name", "").strip()
        lab = (entry.get("lab_or_pi") or "").strip()
        if not lab or lab.lower().startswith("unknown"):
            out[name] = None
            continue
        m = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z\-áíéó]+)+)", lab)
        out[name] = m.group(1) if m else lab.split("(")[0].strip()
    return out


def topic_affinity(reviewer_tokens: set[str], title: str, abstract_text: str) -> int:
    """Count reviewer match-tokens hit in title+abstract. Title matches count 2×.

    Each token contributes at most once — coverage over repetition. `set` input
    means order doesn't matter and dupes are pre-collapsed.
    """
    if not reviewer_tokens:
        return 0
    title_lc = (title or "").lower()
    body_lc = (abstract_text or "").lower()
    score = 0
    for tok in reviewer_tokens:
        if tok in title_lc:
            score += 2
        elif tok in body_lc:
            score += 1
    return score


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


def assign_round_robin(rows, reviews_per_abstract, reviewer_topics=None,
                       reviewer_labs=None):
    """Balance-first + COI-aware + topic-affinity + same-lab diversity assignment.

    For each abstract in order, greedily pick `reviews_per_abstract` reviewers
    using sort key (load, -affinity, tiebreak):
      1. lowest current load first (keeps loads within ±1 across the roster)
      2. best topic-affinity as tiebreaker within same load
      3. deterministic round-robin fallback
    Then enforce same-lab diversity: skip any reviewer whose PI/lab already has
    a reviewer picked for this abstract. Reviewers with unknown labs bypass the
    constraint. If diversity leaves the abstract underfilled, relax it and log.
    `reviewer_topics=None` disables affinity (pure round-robin, back-compat).
    `reviewer_labs=None` disables the diversity constraint.

    Returns (assignments, load, unfilled, total_affinity, samelab_relaxations).
    """
    reviewer_names = [n for n, _ in REVIEWERS]
    load = {n: 0 for n in reviewer_names}
    tiebreak = {n: i for i, n in enumerate(reviewer_names)}
    topics = reviewer_topics or {}
    labs = reviewer_labs or {}

    assignments = []
    unfilled = []
    samelab_relaxations = []  # abstract_ids that had to break the same-lab rule
    total_affinity = 0

    for r in rows:
        affil_text = " ".join([
            r.get("Affiliation", "") or "",
            r.get("Authors with affiliations (One per line)", "") or "",
        ]).strip()
        title = r.get("Title", "") or ""
        body = r.get("Abstract", "") or ""

        aff = {n: topic_affinity(topics.get(n, []), title, body) for n in reviewer_names}

        # Eligible pool: not COI-conflicted, sorted by (load, -affinity, tiebreak).
        eligible = sorted(
            (n for n in reviewer_names
             if not has_coi(REVIEWER_INSTS[n], affil_text)),
            key=lambda n: (load[n], -aff[n], tiebreak[n]),
        )

        # Greedy pick with same-lab diversity constraint.
        picked = []
        picked_labs = set()
        for n in eligible:
            if len(picked) >= reviews_per_abstract:
                break
            n_lab = labs.get(n)
            if n_lab is not None and n_lab in picked_labs:
                continue
            picked.append(n)
            if n_lab is not None:
                picked_labs.add(n_lab)

        # Relaxation 1: if diversity blocked us short, fill from remaining
        # eligible ignoring the same-lab rule (better than COI-conflicted).
        if len(picked) < reviews_per_abstract:
            samelab_relaxations.append(r["abstract_id"])
            for n in eligible:
                if n in picked:
                    continue
                picked.append(n)
                if len(picked) >= reviews_per_abstract:
                    break

        # Relaxation 2: fully unfilled — pull from COI-conflicted (rare).
        gap = reviews_per_abstract - len(picked)
        if gap > 0:
            unfilled.append(r["abstract_id"])
            fallback_pool = sorted(
                (n for n in reviewer_names if n not in picked),
                key=lambda n: (load[n], -aff[n], tiebreak[n]),
            )
            picked.extend(fallback_pool[:gap])

        for n in picked:
            load[n] += 1
            coi_flag = has_coi(REVIEWER_INSTS[n], affil_text)
            assignments.append((r["abstract_id"], n, coi_flag, aff[n]))
            total_affinity += aff[n]

    return assignments, load, unfilled, total_affinity, samelab_relaxations


def ingest(csv_path: Path, zip_path: Path, reviews_per_abstract: int,
           topic_aware: bool = True) -> None:
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

    # Reviewer-facing (unblinded — authors + affiliation shown per chair decision Aug 15)
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
                r.get("Affiliation", "").strip(),
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

    # Reviewer topics + labs for affinity scoring + same-lab diversity (optional)
    reviewer_topics = load_reviewer_topics(TOPICS_YAML) if topic_aware else {}
    reviewer_labs = load_reviewer_labs(TOPICS_YAML) if topic_aware else {}
    missing_topics = [n for n, _ in REVIEWERS if n not in reviewer_topics] if topic_aware else []

    # Assignments
    assignments, load, unfilled, total_affinity, samelab_relaxations = assign_round_robin(
        rows, reviews_per_abstract,
        reviewer_topics if topic_aware else None,
        reviewer_labs if topic_aware else None,
    )
    assign_csv = BUILD_DIR / "assignments.csv"
    with assign_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["abstract_id", "reviewer", "coi_flag", "topic_affinity"])
        for aid, rn, coi, aff in assignments:
            w.writerow([aid, rn, "TRUE" if coi else "FALSE", aff])

    # Summary text file for the chairs
    n_zero_affinity = sum(1 for _, _, _, aff in assignments if aff == 0) if topic_aware else 0
    n_high_affinity = sum(1 for _, _, _, aff in assignments if aff >= 3) if topic_aware else 0
    mean_affinity = total_affinity / max(len(assignments), 1) if topic_aware else 0.0
    summary_path = BUILD_DIR / "assignments_summary.txt"
    lines = [
        f"submissions:          {len(rows)}",
        f"pdfs matched:         {n_pdfs} ({n_pdfs*100//max(len(rows),1)}%)",
        f"reviews per abstract: {reviews_per_abstract}",
        f"total review slots:   {len(rows) * reviews_per_abstract}",
        f"reviewers:            {len(REVIEWERS)}",
        f"target load / reviewer: ~{len(rows) * reviews_per_abstract // len(REVIEWERS)}",
        f"topic-aware:          {'YES' if topic_aware else 'NO'}",
    ]
    if topic_aware:
        lines.extend([
            f"reviewer_topics.yaml: {TOPICS_YAML.relative_to(ROOT)}"
            f"{' (MISSING — treated as empty)' if not reviewer_topics else ''}",
            f"total topic affinity: {total_affinity}  (mean {mean_affinity:.2f} per pair)",
            f"pairs with zero affinity: {n_zero_affinity} / {len(assignments)}",
            f"pairs with high affinity (≥3): {n_high_affinity} / {len(assignments)}",
        ])
        if missing_topics:
            lines.append(f"reviewers missing from topics yaml ({len(missing_topics)}): {', '.join(missing_topics)}")
        if samelab_relaxations:
            lines.append(f"same-lab diversity relaxed for {len(samelab_relaxations)} abstract(s): {', '.join(samelab_relaxations[:20])}{'...' if len(samelab_relaxations) > 20 else ''}")
    lines.extend([
        "",
        "load per reviewer (should cluster tightly around the target):",
    ])
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
    p.add_argument("--no-topic-aware", dest="topic_aware", action="store_false",
                   help="disable topic-affinity scoring; pure round-robin (v1 behavior)")
    p.set_defaults(topic_aware=True)
    args = p.parse_args()
    ingest(args.csv, args.zip, args.reviews_per_abstract, topic_aware=args.topic_aware)


if __name__ == "__main__":
    main()
