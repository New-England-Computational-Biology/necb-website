#!/usr/bin/env python3
"""Aggregate NECB 2026 abstract-review scores into a ranked selection sheet.

Reads a Scores CSV (one row per review, exported from Google Forms/Sheets or the
ISCB platform), computes per-abstract summaries, ranks them, and flags
disagreements for chair review.

Expected input columns (case-insensitive; extras ignored):

    abstract_id       — string / int, unique per abstract
    reviewer          — string (any format, e.g. 'Kit Gallagher')
    significance      — int 1-5
    rigor             — int 1-5
    clarity           — int 1-5
    fit               — int 1-5
    recommendation    — one of {'talk', 'poster', 'reject'}   (case-insensitive)
    confidence        — one of {'low', 'med', 'high'}          (case-insensitive)
    rationale         — free text (kept, not aggregated)

Output CSV (--out, default `ranked.csv`) columns:

    abstract_id, n_reviews,
    mean_significance, mean_rigor, mean_clarity, mean_fit,
    mean_overall,          # recommendation encoded talk=3, poster=2, reject=1
    mean_confidence,       # low=1, med=2, high=3
    weighted_score,        # mean_overall * mean_confidence
    stdev_overall,
    n_talk, n_poster, n_reject,
    disagreement_flag,     # 'talk_vs_reject' or 'stdev>1.5' or ''
    rationales             # joined with ' | '

Usage:

    python scripts/aggregate.py scores.csv --out ranked.csv
    python scripts/aggregate.py scores.csv --talks 8    # tag top-8 as 'talk'

Requires: pandas.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


REC_MAP = {"talk": 3, "poster": 2, "reject": 1}
CONF_MAP = {"low": 1, "med": 2, "medium": 2, "high": 3}

REQUIRED_COLS = [
    "abstract_id", "reviewer",
    "significance", "rigor", "clarity", "fit",
    "recommendation", "confidence",
]


def load_scores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names to lower snake case
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"missing required columns: {missing}\nhave: {list(df.columns)}")

    # Normalize the enum columns
    df["recommendation"] = df["recommendation"].astype(str).str.strip().str.lower()
    df["confidence"] = df["confidence"].astype(str).str.strip().str.lower()

    bad_rec = ~df["recommendation"].isin(REC_MAP)
    if bad_rec.any():
        raise SystemExit(
            f"unknown recommendation values in rows {df.index[bad_rec].tolist()}: "
            f"{df.loc[bad_rec, 'recommendation'].unique().tolist()}"
        )
    bad_conf = ~df["confidence"].isin(CONF_MAP)
    if bad_conf.any():
        raise SystemExit(
            f"unknown confidence values in rows {df.index[bad_conf].tolist()}: "
            f"{df.loc[bad_conf, 'confidence'].unique().tolist()}"
        )

    df["rec_enc"] = df["recommendation"].map(REC_MAP)
    df["conf_enc"] = df["confidence"].map(CONF_MAP)

    # Rationale is optional; fill missing so joins don't drop rows
    if "rationale" not in df.columns:
        df["rationale"] = ""
    else:
        df["rationale"] = df["rationale"].fillna("").astype(str)

    return df


def aggregate(df: pd.DataFrame, stdev_threshold: float = 1.5) -> pd.DataFrame:
    grouped = df.groupby("abstract_id")

    rows = []
    for aid, g in grouped:
        n = len(g)
        rec_counts = g["recommendation"].value_counts().to_dict()
        n_talk = rec_counts.get("talk", 0)
        n_poster = rec_counts.get("poster", 0)
        n_reject = rec_counts.get("reject", 0)

        mean_overall = g["rec_enc"].mean()
        stdev_overall = g["rec_enc"].std(ddof=0) if n > 1 else 0.0

        flag = ""
        if n_talk > 0 and n_reject > 0:
            flag = "talk_vs_reject"
        elif stdev_overall > stdev_threshold:
            flag = f"stdev>{stdev_threshold}"

        rows.append({
            "abstract_id": aid,
            "n_reviews": n,
            "mean_significance": round(g["significance"].mean(), 2),
            "mean_rigor": round(g["rigor"].mean(), 2),
            "mean_clarity": round(g["clarity"].mean(), 2),
            "mean_fit": round(g["fit"].mean(), 2),
            "mean_overall": round(mean_overall, 2),
            "mean_confidence": round(g["conf_enc"].mean(), 2),
            "weighted_score": round(mean_overall * g["conf_enc"].mean(), 2),
            "stdev_overall": round(stdev_overall, 2),
            "n_talk": n_talk,
            "n_poster": n_poster,
            "n_reject": n_reject,
            "disagreement_flag": flag,
            "rationales": " | ".join(g["rationale"].tolist()).strip(),
        })

    out = pd.DataFrame(rows).sort_values(
        by=["weighted_score", "mean_significance"], ascending=[False, False]
    )
    return out


def tag_selection(ranked: pd.DataFrame, n_talks: int) -> pd.DataFrame:
    """Add a `selection` column: 'talk' for top-N, 'poster' for the rest above the reject line."""
    ranked = ranked.copy()
    ranked["selection"] = "poster"
    ranked.iloc[:n_talks, ranked.columns.get_loc("selection")] = "talk"
    # Anything the reviewers wanted rejected (majority reject) drops to 'reject'
    majority_reject = ranked["n_reject"] > (ranked["n_reviews"] - ranked["n_reject"])
    ranked.loc[majority_reject, "selection"] = "reject"
    return ranked


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("scores_csv", type=Path, help="Path to the Scores CSV")
    p.add_argument("--out", type=Path, default=Path("ranked.csv"),
                   help="Output CSV path (default: ranked.csv)")
    p.add_argument("--talks", type=int, default=None,
                   help="If set, tag top-N as 'talk' in a `selection` column")
    p.add_argument("--stdev-threshold", type=float, default=1.5,
                   help="Overall-score stdev above which to flag disagreement (default: 1.5)")
    args = p.parse_args(argv)

    df = load_scores(args.scores_csv)
    ranked = aggregate(df, stdev_threshold=args.stdev_threshold)
    if args.talks is not None:
        ranked = tag_selection(ranked, args.talks)

    ranked.to_csv(args.out, index=False)

    # Print a short summary to stderr for the operator
    n = len(ranked)
    flagged = (ranked["disagreement_flag"] != "").sum()
    print(f"aggregated {n} abstracts → {args.out}", file=sys.stderr)
    print(f"  disagreement-flagged: {flagged}", file=sys.stderr)
    if args.talks is not None:
        counts = ranked["selection"].value_counts().to_dict()
        print(f"  selection: {counts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
