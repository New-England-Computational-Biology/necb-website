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
# abstract institutions gets collapsed so it doesn't dominate the frame.
KEEP_MIN = 2
top_pairs = [(k, v) for k, v in merged.most_common() if v >= KEEP_MIN]
tail_items = [(k, v) for k, v in merged.items() if v < KEEP_MIN]
items = list(top_pairs)
if tail_items:
    items.append(
        (f"Other · {len(tail_items)} institutions "
         f"(1 abstract each)", sum(v for _, v in tail_items))
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


def short_label(label, count, rw, rh, fs):
    """Return a display string that fits inside the rect, or '' when
    nothing reasonable fits. Also breaks into multiple lines when the
    rect is squarish and the label is multi-word."""
    area = rw * rh
    if area < 8:
        return ""
    # Character budget scales with rect width and inverse of font size.
    # 100pt of horizontal coord ≈ 11 inches at figsize=(11,6.5) so ~7
    # chars per horizontal unit at fs=10.
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
    # Cap number of lines to what fits vertically.
    max_lines = max(1, int(rh * 8 / fs))
    lines = lines[:max_lines]
    if not lines:
        return ""
    # If we clipped, add an ellipsis on the last line.
    if len(lines) < len(label.split()) or any(
        len(l) > max_chars_per_line for l in lines
    ):
        last = lines[-1]
        if len(last) > max_chars_per_line - 1:
            last = last[: max_chars_per_line - 1]
        # Suppress ellipsis when clipping is silly (e.g. single-word truncation)
        lines[-1] = last
    return "\n".join(lines)


for i, ((label, count), (rx, ry, rw, rh)) in enumerate(zip(items, rects)):
    if label.startswith("Other · "):
        color = OTHER_TILE
        txt_col = C_INK
    elif i < 3:
        color = FUCHSIA_TILE
        txt_col = "white"
    else:
        color = NAVY_TILE
        txt_col = "white"
    ax.add_patch(plt.matplotlib.patches.Rectangle(
        (rx, ry), rw, rh, facecolor=color, edgecolor=C_GROUND,
        linewidth=1.6))
    area = rw * rh
    fs = min(13, max(7, 0.8 * (area ** 0.5)))
    # Very small boxes get just the count.
    if fs < 8:
        ax.text(rx + rw / 2, ry + rh / 2, str(count),
                ha="center", va="center", fontsize=max(6, fs),
                weight="700", color=txt_col)
        continue
    display = short_label(label, count, rw, rh, fs)
    if not display:
        ax.text(rx + rw / 2, ry + rh / 2, str(count),
                ha="center", va="center", fontsize=fs, weight="700",
                color=txt_col)
        continue
    n_lines = display.count("\n") + 1
    # Nudge label up, count down.
    ax.text(rx + rw / 2, ry + rh / 2 + fs * 0.05 * (n_lines + 1),
            display, ha="center", va="center", fontsize=fs, weight="700",
            color=txt_col, linespacing=1.05)
    ax.text(rx + rw / 2,
            ry + rh / 2 - fs * (0.35 + 0.28 * n_lines),
            str(count), ha="center", va="center",
            fontsize=fs * 0.88, weight="700",
            color=txt_col, alpha=0.85)

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

fig = plt.figure(figsize=(12, 6.5))
gs = fig.add_gridspec(2, 2, width_ratios=[2.2, 1],
                      height_ratios=[3, 1.1], hspace=0.28, wspace=0.15)

# --- LEFT (top): Northeast bubble map ---------------------------------
axm = fig.add_subplot(gs[0, 0])
axm.set_facecolor(C_GROUND)

NE_LON = (-74.0, -69.8)
NE_LAT = (41.0, 44.0)
axm.set_xlim(*NE_LON); axm.set_ylim(*NE_LAT)
axm.set_aspect("equal")
axm.set_xticks([]); axm.set_yticks([])
for s in axm.spines.values(): s.set_edgecolor(C_RULE); s.set_linewidth(0.8)
axm.grid(False)

# Rough state borders (straight-line approximations)
def _line(x1, y1, x2, y2, **kw):
    axm.plot([x1, x2], [y1, y2], color=C_RULE, linewidth=0.9, **kw)
_line(-73.5, 41.0, -73.5, 43.55)     # NY–VT/MA border
_line(-73.5, 42.75, -70.9, 42.75)    # MA–NH/VT border
_line(-73.5, 42.03, -71.35, 42.03)   # MA–CT border
_line(-71.4, 42.03, -71.4, 41.35)    # MA–RI border rough
_line(-71.8, 42.03, -71.8, 41.0)     # CT–RI border
_line(-71.03, 42.55, -71.03, 43.5)   # NH–ME rough
_line(-72.9, 42.75, -72.9, 45.0)     # VT–NH border rough

state_labels = [
    ("MA", -71.5, 42.35), ("NH", -71.7, 43.35),
    ("VT", -73.2, 43.4),  ("CT", -72.7, 41.55),
    ("RI", -71.55, 41.55), ("NY", -73.85, 43.0),
    ("ME", -70.4, 43.7),
]
for lab, lon, lat in state_labels:
    axm.text(lon, lat, lab, fontsize=10, color=C_MUTED, weight="700",
             ha="center", va="center", alpha=0.75, zorder=1)

# Aggregate Greater Boston cluster (Cambridge, Somerville, Medford,
# Brookline, Belmont, Malden, Quincy, Lexington) into one anchor bubble
GREATER_BOSTON = {"Boston", "Cambridge", "Somerville", "Medford",
                  "Brookline", "Belmont", "Malden", "Quincy",
                  "Lexington"}
gb_count = sum(c for k, (_, c) in city_dots.items() if k in GREATER_BOSTON)
gb_lat, gb_lon = 42.36, -71.06  # Boston center

# Plot dots for non-Greater-Boston cities in the frame
labeled = []
for city, ((lat, lon), cnt) in sorted(city_dots.items(),
                                       key=lambda kv: -kv[1][1]):
    if city in GREATER_BOSTON: continue
    if not (NE_LON[0] <= lon <= NE_LON[1] and
            NE_LAT[0] <= lat <= NE_LAT[1]):
        continue
    r = 8 * (cnt ** 0.55)
    axm.scatter([lon], [lat], s=r * 12, color=C_FUCHSIA,
                alpha=0.72, edgecolor="white", linewidth=1.2,
                zorder=5)
    if cnt >= 4:
        labeled.append((city, lon, lat, cnt))

# Greater-Boston anchor bubble
r = 14 * (gb_count ** 0.5)
axm.scatter([gb_lon], [gb_lat], s=r * 20, color=C_FUCHSIA,
            alpha=0.85, edgecolor="white", linewidth=2, zorder=6)
labeled.append(("Greater Boston", gb_lon, gb_lat, gb_count))

# Annotate labels outside the cluster to avoid overlap. Simple heuristic
# — nudge label to the right for eastern cities, left for western ones.
for city, lon, lat, cnt in labeled:
    dx, dy = 0.20, 0.0
    if city == "Greater Boston":
        dx, dy = 0.55, -0.15
    elif city == "Worcester":
        dx, dy = -0.85, 0.0
    elif city == "New Haven":
        dx, dy = -0.75, -0.15
    elif city == "Providence":
        dx, dy = 0.15, -0.35
    axm.annotate(f"{city} · {cnt}", xy=(lon, lat),
                 xytext=(lon + dx, lat + dy),
                 fontsize=10, color=C_INK, weight="700",
                 ha="left" if dx > 0 else "right", va="center", zorder=7,
                 arrowprops=dict(arrowstyle="-", color=C_MUTED,
                                 lw=0.8, alpha=0.7))

axm.set_title("Attendees across the Northeast", loc="left",
              fontsize=13, weight="700", color=C_INK, pad=10)

# --- BELOW map: state inset (moved out of the map axes) --------------
axi = fig.add_subplot(gs[1, 0])
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


state_counts = Counter(zip_to_state(r[ZIP]) for r in rows[1:]
                       if r[12] == "United States" and r[ZIP])
state_counts.pop(None, None)
# Top ~10 states, MA on the far left for context
state_order = ["MA"] + [s for s, _ in state_counts.most_common() if s != "MA"][:9]
state_vals = [state_counts.get(s, 0) for s in state_order]
x_pos = np.arange(len(state_order))
axi.bar(x_pos, state_vals,
        color=[C_FUCHSIA if s == "MA" else C_NAVY for s in state_order])
for i, v in enumerate(state_vals):
    axi.text(i, v + max(state_vals) * 0.03, str(v),
             ha="center", fontsize=8, weight="700", color=C_INK)
axi.set_xticks(x_pos)
axi.set_xticklabels(state_order)
axi.set_title("Attendees by state (top 10)", fontsize=11,
              weight="700", color=C_INK, pad=6, loc="left")
axi.tick_params(axis="both", labelsize=9, colors=C_INK,
                length=0, pad=2)
axi.set_ylim(0, max(state_vals) * 1.18)
axi.grid(axis="y", visible=True, color=C_RULE, linewidth=0.5)
for s in ["top", "right", "left"]:
    axi.spines[s].set_visible(False)
axi.spines["bottom"].set_edgecolor(C_MUTED)

# --- RIGHT: international tiles (spans full height) -----------------
ax2 = fig.add_subplot(gs[:, 1])
ax2.set_facecolor(C_GROUND)
ax2.set_title("International", loc="left",
              fontsize=13, weight="700", color=C_INK, pad=10)
# Big US anchor number at the very top for scale
ax2.text(0.5, 0.94, f"{us_count} US", ha="center", va="center",
         fontsize=16, weight="700", color=C_NAVY,
         transform=ax2.transAxes)
ax2.text(0.5, 0.88, f"({us_count/data.shape[0]*100:.0f}% of registrations)",
         ha="center", va="center", fontsize=9, color=C_MUTED,
         transform=ax2.transAxes, style="italic")

intl_sorted = sorted(intl.items(), key=lambda x: (-x[1], x[0]))
ncols = 2
for i, (country, cnt) in enumerate(intl_sorted):
    r_i, c_i = divmod(i, ncols)
    x = 0.25 + c_i * 0.5
    y = 0.72 - r_i * 0.18
    disc = plt.matplotlib.patches.Circle(
        (x, y + 0.02), radius=0.05,
        transform=ax2.transAxes, color=C_FUCHSIA, zorder=1,
    )
    ax2.add_patch(disc)
    ax2.text(x, y + 0.02, ISO.get(country, "??"),
             ha="center", va="center", fontsize=10, weight="800",
             color="white", transform=ax2.transAxes, zorder=2)
    ax2.text(x, y - 0.08, DISPLAY.get(country, country),
             ha="center", va="center", fontsize=8, color=C_INK,
             weight="600", transform=ax2.transAxes)
    ax2.text(x, y - 0.13, f"{cnt}", ha="center", va="center",
             fontsize=9, color=C_MUTED, weight="700",
             transform=ax2.transAxes)
ax2.text(0.5, 0.02, f"{sum(intl.values())} attendees · "
         f"{len(intl)} countries",
         transform=ax2.transAxes, ha="center", va="bottom",
         fontsize=9, color=C_MUTED, style="italic")
for s in ax2.spines.values(): s.set_visible(False)
ax2.set_xticks([]); ax2.set_yticks([]); ax2.grid(False)

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
