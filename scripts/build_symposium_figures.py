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

# --- Figure 2 · Institutions treemap (by abstract count) ------------------
# Treemap of the institutions contributing accepted abstracts. Each rect
# is sized by the number of accepted abstracts that list the institution
# as the presenting affiliation. Alias-collapsed for common short forms.

def load_sub_affils():
    """Return a Counter of presenting_affiliation across regular + late."""
    aff_counter: Counter = Counter()
    for path in [SUB_CSV, SUB_LATE_CSV]:
        if not path.exists():
            continue
        with open(path) as f:
            for row in __import__("csv").reader(f):
                if len(row) < 4 or not row[0].startswith("A"):
                    continue
                aff = (row[3] or "").strip()
                if not aff or aff == "—":
                    continue
                aff_counter[aff] += 1
    return aff_counter


AFFIL_ALIASES = {
    "MGH": "Massachusetts General Hospital",
    "MGH · HMS": "Massachusetts General Hospital",
    "MGH · HMS · Broad": "Massachusetts General Hospital",
    "Broad Institute of MIT and Harvard": "Broad Institute",
    "Broad": "Broad Institute",
    "Harvard T.H. Chan School of Public Health": "Harvard T.H. Chan",
    "Whitehead Institute for Biomedical Research": "Whitehead Institute",
    "Northeastern University Boston": "Northeastern University",
    "Northeastern University and The University of Illinois Chicago":
        "Northeastern University",
    "University of Massachusetts Medical School": "UMass Chan Medical School",
    "UMass Chan Medical School (formerly UMMS)": "UMass Chan Medical School",
    "Boston University, Bioinformatics Program, Faculty of Computing and Data Sciences":
        "Boston University",
    "Boston University, Faculty of Computing and Data Sciences": "Boston University",
    "Boston University, Bioinformatics Program": "Boston University",
    "Harvard Medical School · Massachusetts General Hospital":
        "Harvard Medical School",
    "Harvard Medical School · Broad Institute": "Harvard Medical School",
    "Harvard": "Harvard University",
    "Broad Institute · Harvard": "Broad Institute",
    "Broad Institute · MIT": "Broad Institute",
    "MIT CSAIL": "MIT",
    "MIT / Whitehead Institute": "MIT",
    "Whitehead Institute, UCLA": "Whitehead Institute",
}

raw_affils = load_sub_affils()

def normalize_affiliation(aff):
    """Collapse punctuation-variant + subunit-variant names to a
    canonical root. First: try exact alias hit. Otherwise: take the
    text before the first ',' or '·' (usually the parent institution)
    and try alias hits on that root too."""
    aff = aff.strip().rstrip(",;.").strip()
    if aff in AFFIL_ALIASES:
        return AFFIL_ALIASES[aff]
    # Root = first segment before ',' or '·'
    root = re.split(r"\s*[·,]\s*", aff, maxsplit=1)[0].strip()
    if root in AFFIL_ALIASES:
        return AFFIL_ALIASES[root]
    return root or aff


merged: Counter = Counter()
for aff, n in raw_affils.items():
    merged[normalize_affiliation(aff)] += n

# Keep every institution with >= 2 abstracts; the long tail of single-
# abstract institutions gets collapsed. The "Other" tile is rendered at
# a compressed size (~top-3 average) so it doesn't swallow the frame —
# the real count still shows inside the tile as text.
KEEP_MIN = 2
top_pairs = [(k, v) for k, v in merged.most_common() if v >= KEEP_MIN]
tail_items = [(k, v) for k, v in merged.items() if v < KEEP_MIN]
items = list(top_pairs)
other_real_count = sum(v for _, v in tail_items)
if tail_items:
    # Compressed footprint = average of the top-3 named tiles, so Other
    # sits alongside them rather than dwarfing them.
    other_display = int(round(
        sum(v for _, v in top_pairs[:3]) / max(3, 1)
    ))
    items.append(
        (f"Other · {len(tail_items)} institutions "
         f"({other_real_count} abstracts)", other_display)
    )


def squarify(values, x, y, w, h):
    """Squarified treemap (Bruls, Huijsen & van Wijk 2000). Returns a
    list of (x, y, w, h) rectangles, one per value, in the input order."""
    total = float(sum(values))
    if total <= 0:
        return []
    scale = (w * h) / total
    scaled = [v * scale for v in values]
    rects = []

    def _worst(row, side):
        r_sum = sum(row)
        r_max = max(row)
        r_min = min(row)
        return max((side ** 2 * r_max) / (r_sum ** 2),
                   (r_sum ** 2) / (side ** 2 * r_min))

    def _layout(row, side, cx, cy, cw, ch):
        # Lay a row along the short side.
        r_sum = sum(row)
        thick = r_sum / side
        rects_out = []
        if cw <= ch:  # row goes horizontally along width
            offset = 0
            for v in row:
                rw = v / thick
                rects_out.append((cx + offset, cy + ch - thick, rw, thick))
                offset += rw
        else:         # row goes vertically along height
            offset = 0
            for v in row:
                rh = v / thick
                rects_out.append((cx, cy + ch - offset - rh, thick, rh))
                offset += rh
        return rects_out, thick

    def _remaining(cx, cy, cw, ch, thick):
        if cw <= ch:
            return cx, cy, cw, ch - thick
        else:
            return cx + thick, cy, cw - thick, ch

    remaining = list(scaled)
    cx, cy, cw, ch = x, y, w, h
    while remaining:
        side = min(cw, ch)
        row = [remaining[0]]
        i = 1
        while i < len(remaining):
            if _worst(row + [remaining[i]], side) <= _worst(row, side):
                row.append(remaining[i])
                i += 1
            else:
                break
        rects_row, thick = _layout(row, side, cx, cy, cw, ch)
        rects.extend(rects_row)
        cx, cy, cw, ch = _remaining(cx, cy, cw, ch, thick)
        remaining = remaining[len(row):]
    return rects


rects = squarify([v for _, v in items], 0, 0, 100, 62)

fig, ax = plt.subplots(figsize=(11, 6.5))
# Uniform navy fill so the treemap reads as one cohesive block.
# Top 3 wear fuchsia to draw the eye. Grey for the "Other" tile.
NAVY_TILE = C_NAVY
FUCHSIA_TILE = C_FUCHSIA
OTHER_TILE = "#C8C8CC"


def short_label(label, count, rw, rh, fs, reserve_lines=1):
    """Return a display string that fits inside the rect while leaving
    `reserve_lines` worth of vertical room for the count text below.
    Returns '' when nothing reasonable fits."""
    area = rw * rh
    if area < 8:
        return ""
    max_chars_per_line = max(5, int(rw * 11 / fs))
    words = label.split()
    lines = []
    line = ""
    for w in words:
        candidate = f"{line} {w}".strip()
        if len(candidate) <= max_chars_per_line:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    # Reserve vertical room for the count. Approx one text line ≈ fs * 1.2
    # in axis units (0.8 chars-per-unit / 1 = fs equiv).
    line_height_axis = fs / 8
    max_label_lines = max(1, int((rh - line_height_axis * reserve_lines)
                                 / line_height_axis))
    lines = lines[:max_label_lines]
    if not lines:
        return ""
    # Silent truncation of an over-long final line (no ellipsis — this is
    # a treemap, not prose).
    last = lines[-1]
    if len(last) > max_chars_per_line:
        lines[-1] = last[:max_chars_per_line]
    return "\n".join(lines)


for i, ((label, count), (rx, ry, rw, rh)) in enumerate(zip(items, rects)):
    if label.startswith("Other · "):
        color = OTHER_TILE
        txt_col = C_INK
    else:
        # All named institutions in one color — no top-3 highlight, so
        # the eye reads the relative size differences directly.
        color = NAVY_TILE
        txt_col = "white"
    ax.add_patch(plt.matplotlib.patches.Rectangle(
        (rx, ry), rw, rh, facecolor=color, edgecolor=C_GROUND,
        linewidth=1.6))
    area = rw * rh
    fs = min(13, max(7, 0.8 * (area ** 0.5)))
    # For the compressed Other tile, hide the (now-misleading) sizing
    # count and let the parenthetical inside the label carry the truth.
    display_count = "" if label.startswith("Other · ") else str(count)
    # Very small boxes get just the count.
    if fs < 8:
        if display_count:
            ax.text(rx + rw / 2, ry + rh / 2, display_count,
                    ha="center", va="center", fontsize=max(6, fs),
                    weight="700", color=txt_col)
        continue
    # Reserve one line of vertical room for the count when we plan to
    # draw it. Anchor the label to the top of the tile and the count to
    # the bottom so wrapped multi-line labels can't push either outside.
    reserve = 1 if display_count else 0
    display = short_label(label, count, rw, rh, fs, reserve_lines=reserve)
    if not display:
        if display_count:
            ax.text(rx + rw / 2, ry + rh / 2, display_count,
                    ha="center", va="center", fontsize=fs, weight="700",
                    color=txt_col)
        continue
    # Small vertical padding
    pad = 0.35
    # Label anchored top-center
    ax.text(rx + rw / 2, ry + rh - pad, display,
            ha="center", va="top", fontsize=fs, weight="700",
            color=txt_col, linespacing=1.05)
    if display_count:
        # Count anchored bottom-center inside the box
        ax.text(rx + rw / 2, ry + pad, display_count,
                ha="center", va="bottom", fontsize=fs * 0.88,
                weight="700", color=txt_col, alpha=0.85)

ax.set_xlim(0, 100); ax.set_ylim(0, 62)
ax.set_aspect("equal")
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values(): s.set_visible(False)
ax.grid(False)
ax.set_title("Institutions contributing accepted abstracts", pad=12)
ax.text(0, -2, f"{len(merged)} institutions · "
        f"{sum(merged.values())} accepted abstracts",
        fontsize=10, color=C_MUTED, style="italic", va="top")
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

# Bubble-map version — hand-placed city coordinates (approx lat/lon) so
# we can plot the New England concentration without a mapping library.
CITY_LATLON = {
    # New England hubs
    "Boston": (42.361, -71.058), "Cambridge": (42.375, -71.106),
    "Worcester": (42.263, -71.802), "Medford": (42.418, -71.106),
    "Somerville": (42.387, -71.099), "Brookline": (42.332, -71.121),
    "Quincy": (42.253, -71.002), "Lowell": (42.632, -71.315),
    "Belmont": (42.395, -71.176), "Lexington": (42.447, -71.229),
    "Malden": (42.427, -71.061), "Ipswich": (42.679, -70.842),
    "Northampton": (42.319, -72.632), "Amherst": (42.372, -72.519),
    "New Haven": (41.308, -72.928), "Hartford": (41.764, -72.685),
    "Storrs": (41.807, -72.251),
    "Providence": (41.824, -71.412),
    "Manchester": (42.991, -71.463), "Hanover": (43.702, -72.289),
    # Northeast broader
    "New York": (40.713, -74.006), "Brooklyn": (40.678, -73.944),
    "Ithaca": (42.443, -76.501), "Princeton": (40.348, -74.659),
    "Philadelphia": (39.953, -75.165), "Pittsburgh": (40.441, -79.996),
    "Baltimore": (39.290, -76.612), "Bethesda": (38.984, -77.094),
    "Washington": (38.907, -77.037),
    # Elsewhere
    "Atlanta": (33.749, -84.388), "Chicago": (41.878, -87.630),
    "Ann Arbor": (42.281, -83.743), "Madison": (43.073, -89.401),
    "Nashville": (36.163, -86.781), "Houston": (29.760, -95.370),
    "Austin": (30.267, -97.743), "Dallas": (32.777, -96.797),
    "Denver": (39.739, -104.990), "Boulder": (40.015, -105.271),
    "Seattle": (47.606, -122.332), "Spring": (30.079, -95.417),
}
us_rows = data[data["Country (Address)"] == "United States"]
city_counts = Counter(
    (r or "").strip() for r in us_rows["City (Address)"].dropna()
)
city_dots = {}
unmapped = 0
for city, cnt in city_counts.items():
    if city in CITY_LATLON:
        city_dots[city] = (CITY_LATLON[city], cnt)
    else:
        unmapped += cnt

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

import json
GEOJSON = ROOT / "docs" / "review" / "build" / "us-states.geojson"


GEOJSON_URL = ("https://raw.githubusercontent.com/PublicaMundi/"
               "MappingAPI/master/data/geojson/us-states.json")


def load_us_states():
    """Return the US states GeoJSON, fetching + caching on first call so
    a fresh checkout builds without a manual download step."""
    if not GEOJSON.exists():
        try:
            import urllib.request
            print(f"fetching US states GeoJSON: {GEOJSON_URL}")
            GEOJSON.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(GEOJSON_URL, timeout=30) as r:
                data = r.read()
            with open(GEOJSON, "wb") as f:
                f.write(data)
            print(f"  cached to {GEOJSON.relative_to(ROOT)}  "
                  f"({len(data)/1024:.0f} KB)")
        except Exception as e:
            print(f"warning: could not fetch US states GeoJSON — {e}")
            return None
    with open(GEOJSON) as f:
        return json.load(f)


# US-state ZIP-code prefix map (rough). Same list used for the state bar.
def zip_to_state_abbr(zc):
    try:
        z = int(str(zc).split("-")[0])
    except Exception:
        return None
    for lo, hi, s in [
        (1000, 2799, "MA"), (2800, 2999, "RI"), (3000, 3899, "NH"),
        (3900, 4999, "ME"), (5000, 5999, "VT"), (6000, 6999, "CT"),
        (7000, 8999, "NJ"), (10000, 14999, "NY"), (15000, 19699, "PA"),
        (19700, 19999, "DE"), (20000, 20599, "DC"), (20600, 21999, "MD"),
        (22000, 24699, "VA"), (27000, 28999, "NC"), (30000, 31999, "GA"),
        (32000, 34999, "FL"), (43000, 45999, "OH"), (46000, 47999, "IN"),
        (48000, 49999, "MI"), (50000, 52999, "IA"), (53000, 54999, "WI"),
        (55000, 56999, "MN"), (60000, 62999, "IL"), (63000, 65999, "MO"),
        (66000, 67999, "KS"), (68000, 69999, "NE"), (75000, 79999, "TX"),
        (80000, 81999, "CO"), (85000, 86999, "AZ"), (90000, 96199, "CA"),
        (97000, 97999, "OR"), (98000, 99499, "WA"),
    ]:
        if lo <= z <= hi:
            return s
    return None


# State name -> abbrev (for GeoJSON "name" field)
STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT",
    "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR",
}
ROWS = rows[1:]
state_counts = Counter()
for r in ROWS:
    if r[12] != "United States":
        continue
    s = zip_to_state_abbr(r[23])
    if s:
        state_counts[s] += 1


fig = plt.figure(figsize=(13, 6.5))
# Two-column layout: New England map on the left, two summary tiles on
# the right (other US + international). Everything else (national US
# choropleth, top-cities bar, world map) is dropped — a single tight NE
# map with bubbles is the story.
gs = fig.add_gridspec(2, 2, width_ratios=[2.6, 1],
                      height_ratios=[1, 1],
                      hspace=0.08, wspace=0.12)

# --- LEFT (spans both rows): Northeast US map with city bubbles -----
# Zoom covers MD/DE/VA through ME so NYC, Washington/Baltimore area
# attendees are included alongside the Boston core.
NE_LON = (-80.5, -68.5)
NE_LAT = (38.0, 45.5)
NE_STATES_SHOWN = {
    "ME", "NH", "VT", "MA", "CT", "RI", "NY", "NJ", "PA",
    "MD", "DE", "DC", "VA", "WV", "OH",  # extras for map continuity
}
axm = fig.add_subplot(gs[:, 0])
axm.set_facecolor(C_GROUND)
axm.set_xlim(*NE_LON); axm.set_ylim(*NE_LAT)
axm.set_aspect(1.3)
axm.set_xticks([]); axm.set_yticks([])
for s in axm.spines.values(): s.set_visible(False)
axm.grid(False)
axm.set_title("Attendees across the Northeast",
              loc="left", fontsize=14, weight="700",
              color=C_INK, pad=10)

# Draw Northeast state polygons in a subtle neutral fill.
gj = load_us_states()
if gj is not None:
    def polys_of(geom):
        t = geom["type"]
        cs = geom["coordinates"]
        return [cs] if t == "Polygon" else cs

    NE_FILL = "#EDECE7"
    NE_EDGE = "#BFBEB7"
    for feat in gj["features"]:
        name = feat["properties"].get("name", "")
        abbr = STATE_NAME_TO_ABBR.get(name, "")
        if abbr not in NE_STATES_SHOWN:
            continue
        for polygon in polys_of(feat["geometry"]):
            for ring in polygon:
                xs = [pt[0] for pt in ring]
                ys = [pt[1] for pt in ring]
                axm.fill(xs, ys, color=NE_FILL, edgecolor=NE_EDGE,
                         linewidth=0.7, zorder=1)
        # State labels (spelled-out name at centroid, muted)
        first_ring = polys_of(feat["geometry"])[0][0]
        cx = sum(pt[0] for pt in first_ring) / len(first_ring)
        cy = sum(pt[1] for pt in first_ring) / len(first_ring)
        if NE_LON[0] < cx < NE_LON[1] and NE_LAT[0] < cy < NE_LAT[1]:
            # Tiny NE states get their label pinned outside the crowded
            # Boston-area cluster where the big bubble sits.
            NUDGE = {
                "MA": (-71.5, 42.30),   # nudge left so bubble covers it less
                "CT": (-72.5, 41.55),
                "RI": (-71.45, 41.65),
                "NH": (-71.55, 43.55),
                "VT": (-72.8, 43.85),
                "DC": (-77.5, 39.15),
                "DE": (-75.5, 38.95),
            }
            lon_lab, lat_lab = NUDGE.get(abbr, (cx, cy))
            axm.text(lon_lab, lat_lab, name,
                     ha="center", va="center",
                     fontsize=8.5, color=C_MUTED, weight="600",
                     alpha=0.8, zorder=2)

# City bubbles — cities aggregated to their (lat, lon), sized by count.
# Greater Boston is one anchor since Cambridge/Somerville/etc. are all
# within a couple of miles and would visually merge anyway.
GREATER_BOSTON = {"Boston", "Cambridge", "Somerville", "Medford",
                  "Brookline", "Belmont", "Malden", "Quincy",
                  "Lexington"}
gb_count = sum(c for k, (_, c) in city_dots.items() if k in GREATER_BOSTON)

# Build final dot list: (label, lat, lon, count).
city_bubbles = [("Greater Boston", 42.36, -71.06, gb_count)]
for city, ((lat, lon), cnt) in city_dots.items():
    if city in GREATER_BOSTON:
        continue
    if NE_LON[0] < lon < NE_LON[1] and NE_LAT[0] < lat < NE_LAT[1]:
        city_bubbles.append((city, lat, lon, cnt))
# Sort by count descending so bigger dots draw on top
city_bubbles.sort(key=lambda t: -t[3])

for label, lat, lon, cnt in city_bubbles:
    r = 60 + 60 * (cnt ** 0.55)  # marker size = area, tuned
    axm.scatter([lon], [lat], s=r, color=C_FUCHSIA,
                alpha=0.85, edgecolor="white", linewidth=1.6,
                zorder=5)

# Label the top few and any that fit; small ones stay silent.
LABEL_MIN = 3
label_positions = {
    "Greater Boston":  (0.6, -0.25),
    "Worcester":       (-0.8, 0.0),
    "Providence":      (0.4, -0.3),
    "New Haven":       (-0.7, -0.15),
    "Lowell":          (0.4, 0.35),
    "New York":        (-0.8, 0.0),
    "Northampton":     (-1.2, 0.1),
    "Washington":      (-1.0, -0.3),
    "Baltimore":       (-1.0, 0.15),
    "Bethesda":        (-1.0, -0.3),
    "Philadelphia":    (-1.2, 0.0),
    "Princeton":       (0.4, 0.0),
}
for label, lat, lon, cnt in city_bubbles:
    if cnt < LABEL_MIN:
        continue
    dx, dy = label_positions.get(label, (0.4, 0.2))
    ha = "left" if dx > 0 else "right"
    axm.annotate(
        f"{label} · {cnt}", xy=(lon, lat),
        xytext=(lon + dx, lat + dy),
        fontsize=10, color=C_INK, weight="700",
        ha=ha, va="center", zorder=6,
        arrowprops=dict(arrowstyle="-", color=C_MUTED,
                        lw=0.7, alpha=0.7),
    )


# --- RIGHT (top): "Other US" summary tile ---------------------------
# Compute other-US count = US total minus everything shown on the NE map.
ne_state_counts = sum(state_counts.get(s, 0) for s in
                      ["MA", "CT", "RI", "NH", "VT", "ME",
                       "NY", "NJ", "PA", "MD", "DE", "DC"])
other_us_count = us_count - ne_state_counts
# Enumerate the far-flung states (outside those 12) for the caption.
FARFLUNG_STATES = [s for s, c in state_counts.most_common()
                   if s not in {"MA", "CT", "RI", "NH", "VT", "ME",
                                "NY", "NJ", "PA", "MD", "DE", "DC"}
                   and c > 0]

axi = fig.add_subplot(gs[1])
axi.set_facecolor(C_GROUND)
# Compute per-state counts from zip codes when present.
ZIP = 23
def zip_to_state(zc):
    try: z = int(str(zc).split("-")[0])
    except: return None
    for lo, hi, s in [
        (1000, 2799, "MA"), (2800, 2999, "RI"), (3000, 3899, "NH"),
        (3900, 4999, "ME"), (5000, 5999, "VT"), (6000, 6999, "CT"),
        (7000, 8999, "NJ"), (10000, 14999, "NY"), (15000, 19699, "PA"),
        (19700, 19999, "DE"), (20000, 20599, "DC"), (20600, 21999, "MD"),
        (22000, 24699, "VA"), (27000, 28999, "NC"), (30000, 31999, "GA"),
        (32000, 34999, "FL"), (43000, 45999, "OH"), (46000, 47999, "IN"),
        (48000, 49999, "MI"), (50000, 52999, "IA"), (53000, 54999, "WI"),
        (55000, 56999, "MN"), (60000, 62999, "IL"), (63000, 65999, "MO"),
        (66000, 67999, "KS"), (68000, 69999, "NE"), (75000, 79999, "TX"),
        (80000, 81999, "CO"), (85000, 86999, "AZ"), (90000, 96199, "CA"),
        (97000, 97999, "OR"), (98000, 99499, "WA"),
    ]:
        if lo <= z <= hi: return s
    return None


import textwrap as _tw
axi.set_facecolor(C_GROUND)
axi.set_xlim(0, 100); axi.set_ylim(0, 100)
axi.set_xticks([]); axi.set_yticks([])
for s in axi.spines.values(): s.set_visible(False)
axi.grid(False)
# Card frame
axi.add_patch(plt.matplotlib.patches.FancyBboxPatch(
    (3, 5), 94, 90,
    boxstyle="round,pad=0.02,rounding_size=1.5",
    facecolor="#FFFFFF", edgecolor=C_RULE, linewidth=1.0,
    transform=axi.transData, zorder=1,
))
axi.text(7, 85, "Other US", fontsize=13, weight="700",
         color=C_INK, ha="left", va="top", zorder=2)
axi.text(7, 62, f"{other_us_count}", fontsize=44, weight="800",
         color=C_NAVY, ha="left", va="center", zorder=2)
axi.text(52, 62, "attendees", fontsize=12, color=C_MUTED,
         weight="600", ha="left", va="center", zorder=2)
n_far = len(FARFLUNG_STATES)
axi.text(7, 38, f"across {n_far} states outside\nthe Northeast",
         fontsize=9.5, color=C_INK, weight="600",
         ha="left", va="top", zorder=2, linespacing=1.3)
axi.text(7, 18,
         "\n".join(_tw.wrap(", ".join(FARFLUNG_STATES), width=28)),
         fontsize=8, color=C_MUTED, style="italic",
         ha="left", va="top", zorder=2, linespacing=1.3)

# --- RIGHT (bottom): "International" summary tile -------------------
ax2 = fig.add_subplot(gs[3])
ax2.set_facecolor(C_GROUND)
ax2.set_xlim(0, 100); ax2.set_ylim(0, 100)
ax2.set_xticks([]); ax2.set_yticks([])
for s in ax2.spines.values(): s.set_visible(False)
ax2.grid(False)
ax2.add_patch(plt.matplotlib.patches.FancyBboxPatch(
    (3, 5), 94, 90,
    boxstyle="round,pad=0.02,rounding_size=1.5",
    facecolor="#FFFFFF", edgecolor=C_RULE, linewidth=1.0,
    transform=ax2.transData, zorder=1,
))
ax2.text(7, 85, "International", fontsize=13, weight="700",
         color=C_INK, ha="left", va="top", zorder=2)
ax2.text(7, 62, f"{sum(intl.values())}", fontsize=44,
         weight="800", color=C_FUCHSIA, ha="left", va="center",
         zorder=2)
ax2.text(30, 62, "attendees", fontsize=12, color=C_MUTED,
         weight="600", ha="left", va="center", zorder=2)
ax2.text(7, 38, f"across {len(intl)} countries",
         fontsize=9.5, color=C_INK, weight="600",
         ha="left", va="top", zorder=2, linespacing=1.3)
_intl_display = [DISPLAY.get(c, c) for c in sorted(intl.keys())]
ax2.text(7, 26,
         "\n".join(_tw.wrap(", ".join(_intl_display), width=28)),
         fontsize=8, color=C_MUTED, style="italic",
         ha="left", va="top", zorder=2, linespacing=1.3)

WORLD_GEOJSON = ROOT / "docs" / "review" / "build" / "world-countries.geojson"
WORLD_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
             "/master/geojson/ne_110m_admin_0_countries.geojson")


def load_world():
    if not WORLD_GEOJSON.exists():
        try:
            import urllib.request
            print(f"fetching world GeoJSON: {WORLD_URL}")
            WORLD_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(WORLD_URL, timeout=45) as r:
                data = r.read()
            with open(WORLD_GEOJSON, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"warning: could not fetch world GeoJSON — {e}")
            return None
    with open(WORLD_GEOJSON) as f:
        return json.load(f)


# Match our country names to Natural Earth's "ADMIN" property.
NAME_TO_NE = {
    "Austria": "Austria", "Belgium": "Belgium",
    "Burkina Faso": "Burkina Faso",
    "Hong Kong SAR China": "Hong Kong S.A.R.",
    "Italy": "Italy", "Peru": "Peru", "Singapore": "Singapore",
    "Taiwan": "Taiwan", "United Kingdom": "United Kingdom",
    "Canada": "Canada", "Germany": "Germany", "France": "France",
    "Japan": "Japan", "China": "China", "India": "India",
    "Nigeria": "Nigeria",
}
# Country-center coordinates for dot placement when polygon lookup is
# unreliable (Hong Kong, Singapore, small states).
COUNTRY_LATLON = {
    "Austria": (47.5, 14.5), "Belgium": (50.6, 4.4),
    "Burkina Faso": (12.4, -1.5), "Hong Kong SAR China": (22.3, 114.2),
    "Italy": (41.9, 12.5), "Peru": (-9.2, -75.0),
    "Singapore": (1.35, 103.8), "Taiwan": (23.7, 121.0),
    "United Kingdom": (54.0, -2.5), "Canada": (56.1, -106.3),
    "Germany": (51.2, 10.5), "France": (46.6, 2.2),
    "Japan": (36.2, 138.3), "China": (35.9, 104.2),
    "India": (20.6, 78.9), "Nigeria": (9.1, 8.7),
}

# (world map removed — simplified to summary tile above)

fig.suptitle("Geographic reach", fontsize=17, weight="700",
             color=C_INK, y=0.98, x=0.06, ha="left")
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
    # Word cloud sized by theme + keyword frequency. We seed a large
    # phrase dictionary with the theme counts (as weight-multiplied
    # terms), and blend in shorter keyword bigrams from raw abstracts
    # so the cloud reads as a mix of headline themes and technical
    # sub-terms.
    from wordcloud import WordCloud

    # Base frequencies: theme label → count
    freqs = dict(theme_items)

    # Add nice-looking multi-word technical terms harvested from the
    # abstracts themselves. Simple bigram/trigram scan on lowercase text.
    TECH_TERMS = [
        "single cell", "spatial transcriptomics", "protein design",
        "language model", "foundation model", "graph neural",
        "flow matching", "gene regulation", "drug discovery",
        "cancer genomics", "immune repertoire", "cell painting",
        "variant effect", "generative model", "deep learning",
        "reinforcement learning", "prompt tuning", "benchmark",
        "electronic health record", "clinical variant",
        "transcription factor", "enhancer", "chromatin", "peptide",
        "neoantigen", "microbiome", "metabolic model",
        "structure prediction", "drug repurposing", "docking",
        "regulatory element", "batch integration",
    ]
    joined = " ".join(str(t or "") + " " + str(a or "")
                      for t, a in zip(subs["title"], subs["abstract"])
                      ).lower()
    for term in TECH_TERMS:
        n = joined.count(term)
        if n >= 2:
            freqs[term.title()] = freqs.get(term.title(), 0) + n * 4

    palette = [C_FUCHSIA, C_NAVY, C_TEAL, C_FUCHSIA_DK]

    def color_fn(word, font_size, position, orientation,
                 random_state=None, **kw):
        return palette[hash(word) % len(palette)]

    wc = WordCloud(
        width=1600, height=900,
        background_color=C_GROUND,
        color_func=color_fn,
        prefer_horizontal=1.0,   # keep everything readable — no rotations
        max_words=60,
        relative_scaling=0.55,
        min_font_size=12,
        collocations=False,
        random_state=42,
    ).generate_from_frequencies(freqs)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.imshow(wc.to_array(), interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("Research themes across accepted abstracts",
                 loc="left", pad=8)
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
