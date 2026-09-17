#!/usr/bin/env python3
"""Generate presentation-quality figures introducing NECB 2026.

Reads Diane's registration report + our submissions CSV and produces
brand-styled PNGs (fuchsia / navy / teal palette on a warm off-white
ground) suitable for the chairs' opening slides. All figures are saved
to static/img/stats/.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REG_XLSX = ROOT / "Registration Report - NECB 2026(1).xlsx"
SUB_CSV = ROOT / "docs" / "review" / "build" / "submissions_paste.csv"
SUB_LATE_CSV = ROOT / "docs" / "review" / "build" / "submissions_paste_late.csv"
OUT = ROOT / "static" / "img" / "stats"
OUT.mkdir(parents=True, exist_ok=True)

# --- brand palette --------------------------------------------------------

C_FUCHSIA = "#B31E4B"
C_FUCHSIA_DK = "#8F1A3E"
C_NAVY = "#1C3D7B"
C_TEAL = "#3B7368"
C_INK = "#14141A"
C_MUTED = "#6B6B6E"
C_RULE = "#E1E1E4"
C_GROUND = "#FDFBF6"

plt.rcParams.update({
    "font.family": ["Avenir Next", "Charter", "Georgia", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.titleweight": "600",
    "axes.labelsize": 11,
    "axes.labelcolor": C_INK,
    "axes.edgecolor": C_MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.facecolor": C_GROUND,
    "figure.facecolor": C_GROUND,
    "xtick.color": C_INK,
    "ytick.color": C_INK,
    "text.color": C_INK,
    "axes.grid": True,
    "grid.color": C_RULE,
    "grid.linewidth": 0.6,
})


def savefig(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight",
                facecolor=C_GROUND)
    print(f"wrote {OUT.relative_to(ROOT)}/{name}.png")


# --- load registration data ----------------------------------------------

wb = openpyxl.load_workbook(str(REG_XLSX), data_only=True)
ws = wb["Sheet1"]
rows = list(ws.iter_rows(values_only=True))
h = rows[0]
data = pd.DataFrame(rows[1:], columns=h)

ALIASES = {
    "MGH": "Massachusetts General Hospital",
    "MGH · HMS": "Massachusetts General Hospital",
    "Broad Institute of MIT and Harvard": "Broad Institute",
    "Broad": "Broad Institute",
    "Harvard T.H. Chan School of Public Health": "Harvard T.H. Chan",
    "Whitehead Institute for Biomedical Research": "Whitehead Institute",
    "Northeastern University Boston": "Northeastern University",
    "Mass General Brigham": "Massachusetts General Hospital",
    "Brigham and Women's Hospital": "Brigham & Women's Hospital",
}
data["Affiliation_clean"] = (
    data["Affiliation"].fillna("Unknown").replace(ALIASES).str.strip()
)

# --- Figure 1 · Registration growth curve --------------------------------

df = data.dropna(subset=["Created At"]).copy()
df["date"] = pd.to_datetime(df["Created At"]).dt.date
by_day = df.groupby("date").size().sort_index()
cumu = by_day.cumsum()

fig, ax = plt.subplots(figsize=(9, 4.5))
dates = pd.to_datetime(list(cumu.index))
ax.fill_between(dates, cumu.values, color=C_FUCHSIA, alpha=0.10)
ax.plot(dates, cumu.values, color=C_FUCHSIA, linewidth=2.4)

ax.axhline(300, color=C_NAVY, linewidth=1.0, linestyle="--", alpha=0.7)
ax.annotate("Initial cap · 300", xy=(dates[0], 300), xytext=(dates[0], 305),
            color=C_NAVY, fontsize=10, weight="600")
ax.axhline(325, color=C_TEAL, linewidth=1.0, linestyle="--", alpha=0.7)
ax.annotate("Extended cap · 325", xy=(dates[0], 325), xytext=(dates[0], 330),
            color=C_TEAL, fontsize=10, weight="600")

final = int(cumu.values[-1])
ax.scatter([dates[-1]], [final], s=120, color=C_FUCHSIA_DK, zorder=5)
ax.annotate(f"  {final} attendees\n  as of Sep 15", xy=(dates[-1], final),
            xytext=(-125, -18), textcoords="offset points",
            fontsize=11, weight="600", color=C_FUCHSIA_DK)

ax.set_title("Registration growth · Jul – Sep 2026")
ax.set_ylabel("Cumulative registrations")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
ax.set_ylim(0, 360)
ax.set_xlim(dates[0] - pd.Timedelta(days=1),
            dates[-1] + pd.Timedelta(days=2))
plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
savefig(fig, "01_registration_growth")
plt.close(fig)

# --- Figure 2 · Top institutions -----------------------------------------

top = data["Affiliation_clean"].value_counts().head(15)
top = top.iloc[::-1]

fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top.index, top.values, color=C_NAVY, edgecolor="none")
for i, v in enumerate(top.values):
    ax.text(v + 0.4, i, str(v), va="center", fontsize=10,
            color=C_INK, weight="600")

ax.set_title("Top 15 institutions represented")
ax.set_xlabel("Registered attendees")
ax.set_xlim(0, top.values.max() * 1.12)
ax.grid(axis="y", visible=False)
savefig(fig, "02_top_institutions")
plt.close(fig)

# --- Figure 3 · Career-stage donut ---------------------------------------

def stage(t):
    if t is None:
        return "Other"
    if "Student" in t: return "Student"
    if "Post-Doc" in t: return "Postdoc"
    if "Academic Professional" in t: return "Faculty / Academic"
    if "Research Staff" in t: return "Research staff"
    if "Industry" in t: return "Industry"
    return "Other"


data["stage"] = data["Registrant Type"].map(stage)
# Force a deterministic order for the donut.
STAGE_ORDER = ["Student", "Postdoc", "Faculty / Academic",
               "Research staff", "Industry", "Other"]
stages = data["stage"].value_counts().reindex(STAGE_ORDER).dropna().astype(int)

STAGE_COLORS = {
    "Student": C_FUCHSIA,
    "Postdoc": C_NAVY,
    "Faculty / Academic": C_TEAL,
    "Research staff": "#B79968",
    "Industry": C_INK,
    "Other": C_MUTED,
}
colors = [STAGE_COLORS[s] for s in stages.index]

fig, ax = plt.subplots(figsize=(7.5, 5.5))
wedges, texts, autotexts = ax.pie(
    stages.values, labels=None, colors=colors, startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.42, edgecolor=C_GROUND, linewidth=3),
    autopct=lambda p: f"{p:.0f}%", pctdistance=0.79,
)
for t in autotexts:
    t.set_color("white")
    t.set_fontsize(11)
    t.set_fontweight("700")
ax.text(0, 0.05, f"{data.shape[0]}", ha="center", va="center",
        fontsize=32, weight="700", color=C_NAVY)
ax.text(0, -0.16, "attendees", ha="center", va="center",
        fontsize=11, color=C_MUTED, weight="600")
handles = [plt.matplotlib.patches.Patch(color=c, label=f"{s}  ({n})")
           for s, n, c in zip(stages.index, stages.values, colors)]
ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
          frameon=False, fontsize=11)
ax.set_title("Attendees by career stage", pad=15)
plt.subplots_adjust(right=0.72)
savefig(fig, "03_career_stage")
plt.close(fig)

# --- Figure 4 · Country reach --------------------------------------------

countries = Counter(data["Country (Address)"].fillna("Unknown"))
intl = {k: v for k, v in countries.items()
        if k not in ("United States", "Unknown")}
us_count = countries.get("United States", 0)

# Country-code medallions instead of emoji flags — matplotlib's default
# fonts don't render color flag emoji, so we use compact ISO codes.
ISO = {
    "Austria": "AT", "Belgium": "BE", "Burkina Faso": "BF",
    "Hong Kong SAR China": "HK", "Italy": "IT", "Peru": "PE",
    "Singapore": "SG", "Taiwan": "TW", "United Kingdom": "GB",
    "Canada": "CA", "Germany": "DE", "France": "FR",
    "Japan": "JP", "China": "CN", "India": "IN", "Nigeria": "NG",
    "Netherlands": "NL", "Switzerland": "CH", "Spain": "ES",
    "Sweden": "SE", "Denmark": "DK", "Norway": "NO",
    "Australia": "AU", "New Zealand": "NZ", "Israel": "IL",
    "Brazil": "BR", "Mexico": "MX", "South Korea": "KR",
    "Ireland": "IE",
}
DISPLAY = {"Hong Kong SAR China": "Hong Kong"}

fig = plt.figure(figsize=(11, 5))
gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 2], wspace=0.28)

# Left panel: US anchor number
ax1 = fig.add_subplot(gs[0])
ax1.set_facecolor(C_GROUND)
ax1.text(0.5, 0.60, f"{us_count}", ha="center", va="center",
         fontsize=64, weight="800", color=C_NAVY, transform=ax1.transAxes)
ax1.text(0.5, 0.32, "United States", ha="center", va="center",
         fontsize=14, color=C_INK, weight="600", transform=ax1.transAxes)
ax1.text(0.5, 0.20, f"{us_count/data.shape[0]*100:.0f}% of registrations",
         ha="center", va="center", fontsize=11,
         color=C_MUTED, transform=ax1.transAxes, style="italic")
for s in ax1.spines.values(): s.set_visible(False)
ax1.set_xticks([]); ax1.set_yticks([]); ax1.grid(False)

# Right panel: international tiles
ax2 = fig.add_subplot(gs[1])
ax2.set_facecolor(C_GROUND)
ax2.set_title("International attendees", loc="left",
              fontsize=13, weight="700", color=C_INK, pad=8)
intl_sorted = sorted(intl.items(), key=lambda x: (-x[1], x[0]))
ncols = 4
for i, (country, cnt) in enumerate(intl_sorted):
    r, c = divmod(i, ncols)
    x = c / ncols + 0.5 / ncols
    y = 0.85 - r * 0.42
    # Fuchsia disc with the ISO country code
    disc = plt.matplotlib.patches.Circle(
        (x, y + 0.03), radius=0.055,
        transform=ax2.transAxes, color=C_FUCHSIA, zorder=1,
    )
    ax2.add_patch(disc)
    ax2.text(x, y + 0.03, ISO.get(country, "??"),
             ha="center", va="center", fontsize=12, weight="800",
             color="white", transform=ax2.transAxes, zorder=2)
    ax2.text(x, y - 0.13, DISPLAY.get(country, country),
             ha="center", va="center", fontsize=10, color=C_INK,
             weight="600", transform=ax2.transAxes)
    ax2.text(x, y - 0.22, f"{cnt}", ha="center", va="center",
             fontsize=11, color=C_MUTED, weight="700",
             transform=ax2.transAxes)
ax2.text(1.0, -0.02, f"{sum(intl.values())} attendees · "
         f"{len(intl)} countries",
         transform=ax2.transAxes, ha="right", va="bottom",
         fontsize=10, color=C_MUTED, style="italic")
for s in ax2.spines.values(): s.set_visible(False)
ax2.set_xticks([]); ax2.set_yticks([]); ax2.grid(False)

fig.suptitle("Geographic reach", fontsize=17, weight="700",
             color=C_INK, y=0.99, x=0.06, ha="left")
savefig(fig, "04_country_reach")
plt.close(fig)

# --- Figure 5 · Abstract topics -----------------------------------------

def load_subs(path):
    # index_col=False stops pandas from stealing the first column as the
    # index when names is shorter than the actual column count.
    return pd.read_csv(path, header=None, index_col=False, names=[
        "aid", "title", "authors", "affil", "abstract",
        "pdf", "keywords", "round", "chair",
    ])


try:
    sub_reg = load_subs(SUB_CSV)
    sub_late = (load_subs(SUB_LATE_CSV) if SUB_LATE_CSV.exists()
                else pd.DataFrame(columns=sub_reg.columns))
    subs = pd.concat([sub_reg, sub_late], ignore_index=True)
except Exception as e:
    print("skipping topics fig — CSV parse failed:", e)
    subs = pd.DataFrame(columns=["keywords"])

# Categorize each abstract into one of the six program session themes.
# Uses keyword/title/abstract-text matching. Abstracts that don't match
# any theme fall into "Other methods & tools".
THEMES = [
    ("Single-cell & spatial",       ["single-cell", "single cell", "scrna", "sc-rna",
                                     "spatial transcript", "cell atlas", "cellular",
                                     "cell type", "trajectory", "spatial",
                                     "cell painting", "flow cytometry"]),
    ("Protein design & function",   ["protein design", "protein language", "protein structure",
                                     "protein function", "enzyme", "binder", "de novo",
                                     "structure prediction", "protein-protein", "alphafold",
                                     "esmfold", "protein engineering", "docking",
                                     "protein stability"]),
    ("Genomics & regulation",       ["gene regulat", "regulatory", "transcription factor",
                                     "chromatin", "enhancer", "epigenetic", "motif",
                                     "variant effect", "gwas", "expression prediction",
                                     "regulator", "eqtl", "atac"]),
    ("Immunology & vaccines",       ["antibody", "immune", "immunolog", "vaccine",
                                     "t cell", "b cell", "hla", "peptide-hla", "mhc",
                                     "repertoire", "tcr", "bcr", "neoantigen"]),
    ("Clinical & translational",    ["clinical", "patient", "diagnos", "prognos",
                                     "cancer", "tumor", "cardio", "disease", "therapy",
                                     "translational", "drug", "biomarker", "risk",
                                     "survival", "ehr", "electronic health"]),
    ("AI methods & applications",   ["language model", "foundation model", "llm",
                                     "diffusion", "flow matching", "transformer",
                                     "graph neural", "attention", "reinforcement",
                                     "autoencoder", "vae", "generative", "benchmark",
                                     "agent", "deep learning", "neural network"]),
    ("Systems & networks",          ["network", "pathway", "module", "interaction",
                                     "metabolic", "microbi", "ecolog", "systems bio"]),
]

def classify_abstract(row):
    txt = " ".join([
        str(row.get("title", "") or ""),
        str(row.get("abstract", "") or ""),
        str(row.get("keywords", "") or ""),
    ]).lower()
    matches = []
    for theme, needles in THEMES:
        if any(n in txt for n in needles):
            matches.append(theme)
    return matches or ["Other"]

# Each abstract can belong to more than one theme — we count all matches so
# the total exceeds the abstract count but every bar reads as a real theme.
theme_counts = Counter()
for _, row in subs.iterrows():
    for t in classify_abstract(row):
        theme_counts[t] += 1

# Sort by count desc, drop 'Other' unless nothing matched
theme_items = [(t, c) for t, c in theme_counts.most_common() if t != "Other"]

if theme_items:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    labels, counts = zip(*theme_items)
    ax.barh(labels[::-1], counts[::-1], color=C_TEAL)
    for i, v in enumerate(counts[::-1]):
        ax.text(v + 0.4, i, str(v), va="center", fontsize=10,
                color=C_INK, weight="600")
    ax.set_title("Research themes across accepted abstracts")
    ax.set_xlabel("Abstracts (a single abstract may span themes)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(counts) * 1.14)
    savefig(fig, "05_abstract_topics")
    plt.close(fig)

# --- Figure 6 · At-a-glance stat tiles ----------------------------------

n_intl = sum(v for k, v in countries.items()
             if k not in ("United States", "Unknown"))
n_countries = 1 + len([k for k in countries if k not in
                       ("United States", "Unknown")])
n_institutions = data["Affiliation_clean"].nunique()

stats = [
    (f"{data.shape[0]}",    "registered\nattendees"),
    ("~200",                 "accepted\nabstracts"),
    ("23",                   "selected\ntalks"),
    ("11",                   "keynote & invited\nspeakers"),
    ("175",                  "poster\npresentations"),
    (f"{n_countries}",       "countries\nrepresented"),
    (f"{n_institutions}",    "institutions"),
    ("Oct 1–2",              "2026 · Cambridge,\nMassachusetts"),
]
fig, axes = plt.subplots(2, 4, figsize=(12, 5.5))
axes = axes.flatten()
tile_colors = [C_FUCHSIA, C_NAVY, C_TEAL, C_FUCHSIA_DK,
               C_NAVY, C_FUCHSIA, C_TEAL, C_FUCHSIA_DK]
for ax, (num, lab), col in zip(axes, stats, tile_colors):
    ax.set_facecolor(C_GROUND)
    ax.text(0.5, 0.60, num, ha="center", va="center",
            fontsize=40, weight="800", color=col,
            transform=ax.transAxes)
    ax.text(0.5, 0.18, lab, ha="center", va="center",
            fontsize=12, color=C_INK, transform=ax.transAxes,
            linespacing=1.3)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(False)
fig.suptitle("NECB 2026 · at a glance", fontsize=17, weight="700",
             color=C_INK, y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.94])
savefig(fig, "06_at_a_glance")
plt.close(fig)

print(f"\nDone. All figures in {OUT.relative_to(ROOT)}/")
