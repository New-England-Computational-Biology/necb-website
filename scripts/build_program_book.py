#!/usr/bin/env python3
"""Build docs/review/program-book.md from schedule + speakers + submissions.

Downstream pipeline (unchanged): this script -> program-book.md ->
scripts/render_pdf.py -> PDF via pandoc+typst, styled by
scripts/templates/packet.typ (fuchsia H1s, navy H2s, teal H3s, Charter
body, Avenir Next display, US Letter 1in margins).

Inputs:
  data/program.yaml
  data/speakers.yaml
  data/organizers.yaml
  data/keyDates.yaml
  docs/review/build/submissions_paste.csv       (197 regular abstracts)
  docs/review/build/submissions_paste_late.csv  (25 late-breaking)
  docs/review/build/decisions_posters.csv       (accepted-poster ids,
      user-produced from Luca's 'Accepted posters' sheet tab;
      optional — if missing the book still builds with schedule + talks
      + speakers and warns.)

Output:
  docs/review/program-book.md
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "docs" / "review" / "build"
OUT = ROOT / "docs" / "review" / "program-book.md"

CSV_REG = BUILD / "submissions_paste.csv"
CSV_LATE = BUILD / "submissions_paste_late.csv"
POSTERS_CSV = BUILD / "decisions_posters.csv"
POSTER_SESSIONS = DATA / "posterSessions.yaml"
WITHDRAWALS = BUILD / "withdrawals.csv"

CONF_TITLE = "NECB 2026"
CONF_SUBTITLE = "New England Computational Biology Symposium"
CONF_DATES = "October 1–2, 2026"
CONF_VENUE = "Cambridge, MA"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_yaml(name: str):
    with open(DATA / name) as f:
        return yaml.safe_load(f)


def _unescape_lines(s: str) -> str:
    """For fields where newlines are structural delimiters (author list,
    affiliation list): each literal '\\n' becomes a single real newline.
    Tab escapes similarly. Downstream splitters read on real newlines."""
    return s.replace("\\n", "\n").replace("\\t", "\t")


import re as _re


def _unescape_prose(s: str) -> str:
    """For running prose (abstract body): the ISCB form encodes
    paragraph breaks as literal '\\n\\n' but many authors also submit
    manually wrapped text where a single '\\n' at ~80 chars is a soft
    line break within a paragraph (see A076, A172, A185, A221).

    Strategy: split on paragraph markers (either escaped '\\n\\n' or
    real '\\n\\n'), then flatten every remaining '\\n' or real newline
    inside a paragraph to a single space. This preserves author-intended
    paragraph structure while healing the ragged soft-wrap that would
    otherwise render as blank lines between every wrapped source line."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    parts = _re.split(r"\\n\\n|\n\n", s)
    out = []
    for p in parts:
        p = _re.sub(r"\\n|\n|\\t|\t", " ", p)
        p = " ".join(p.split())
        if p:
            out.append(p)
    return "\n\n".join(out)


def _flatten_line(s: str) -> str:
    """For fields that must be a single line (title): flatten any
    embedded whitespace escapes to spaces."""
    return " ".join(s.replace("\\n", " ").replace("\\t", " ").split())


def load_submissions() -> dict[str, dict]:
    """Read both submissions_paste*.csv into a dict keyed by abstract_id.

    Layout (both CSVs, no header row):
        0 abstract_id | 1 title | 2 authors | 3 presenting_affiliation
        4 abstract_text | 5 pdf_link | 6 topic_keywords
        7 round | 8 chair_notes
    """
    subs: dict[str, dict] = {}
    for path, round_ in [(CSV_REG, "regular"), (CSV_LATE, "late-breaking")]:
        if not path.exists():
            sys.exit(f"error: missing {path.relative_to(ROOT)}")
        with open(path) as f:
            for row in csv.reader(f):
                if len(row) < 8 or not row[0].strip().startswith("A"):
                    continue
                aid = row[0].strip()
                subs[aid] = {
                    "title": _flatten_line(row[1]).strip(),
                    "authors": _unescape_lines(row[2]),
                    "affiliation": _flatten_line(row[3]).strip(),
                    "abstract": _unescape_prose(row[4]).strip(),
                    "has_pdf": row[5].strip() != "—",
                    "round": round_,
                }
    return subs


def load_withdrawn_ids() -> set[str]:
    """Read abstract IDs marked as withdrawn (or promoted-out-of-poster).

    docs/review/build/withdrawals.csv columns:
        abstract_id, type, name, email, withdrawn_on, note
    Header row present. Missing file returns an empty set.
    """
    if not WITHDRAWALS.exists():
        return set()
    ids: set[str] = set()
    with open(WITHDRAWALS) as f:
        for i, row in enumerate(csv.reader(f)):
            if i == 0 or not row:
                continue
            aid = row[0].strip()
            if aid.startswith("A"):
                ids.add(aid)
    return ids


def load_poster_ids() -> list[str]:
    """Preferred source: data/posterSessions.yaml (auto-generated by
    allocate_posters.py; already excludes withdrawals + promoted-to-talk).

    Falls back to decisions_posters.csv if the yaml is not present.
    """
    if POSTER_SESSIONS.exists():
        y = yaml.safe_load(POSTER_SESSIONS.read_text())
        ids: list[str] = []
        seen: set[str] = set()
        for day in y.get("days", []):
            for p in day.get("posters", []):
                aid = p.get("abstract_id", "").strip()
                if aid.startswith("A") and aid not in seen:
                    seen.add(aid)
                    ids.append(aid)
        return ids
    if not POSTERS_CSV.exists():
        return []
    ids: list[str] = []
    with open(POSTERS_CSV) as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    # Detect a header row by looking for an obvious label in row 0
    first_cell = rows[0][0].strip().lower()
    body = rows[1:] if first_cell in {"abstract_id", "id"} else rows
    for row in body:
        if not row:
            continue
        aid = row[0].strip()
        if aid.startswith("A"):
            ids.append(aid)
    return ids


def load_poster_day_map() -> dict[str, tuple[str, str]]:
    """Map abstract_id -> (day_label, session_time) for accepted posters,
    so each poster abstract can carry its session label like talks do.
    """
    if not POSTER_SESSIONS.exists():
        return {}
    y = yaml.safe_load(POSTER_SESSIONS.read_text())
    m: dict[str, tuple[str, str]] = {}
    for day in y.get("days", []):
        label = day.get("label", "")
        time = day.get("time", "")
        for p in day.get("posters", []):
            aid = p.get("abstract_id", "").strip()
            if aid:
                m[aid] = (label, time)
    return m


# ---------------------------------------------------------------------------
# Author formatting
# ---------------------------------------------------------------------------

def _split_authors(raw: str) -> list[str]:
    """Split the free-text authors field into a list of names.

    The ISCB export uses several conventions across submissions:
      - "Yuanqi Du, Microsoft Research" (single, comma-joined with affil)
      - "Bowen Jing, MIT CSAIL\nAnna Sappington, MIT CSAIL, HMS\n..."
      - "Arush Ramteke (Courant Institute...)\nSimon Liu (Courant...)\n..."
      - "Payton Bock* — Boston University\nJackson Smith — Boston..."
      - "Justin Delano, HMS\nPatrick Cann, Johns Hopkins\t\t\n..."

    Strategy: split on real newlines and tabs, then strip trailing
    affiliation attached with em-dash / en-dash / hyphen-with-spaces /
    open-paren / a comma. Drop the presenter '*' marker.
    """
    # Bullet glyphs the ISCB form users sometimes prefix each author with
    # (unicode bullet, hyphen-bullet, en/em dash, asterisk, ASCII dash…).
    BULLETS = "•·⁃∙◦▪▫●○*-–—+"
    # Superscript digits used as author→affiliation markers. Covers the
    # Latin-1 legacy trio (¹²³) and the Unicode superscript block (⁰⁴-⁹).
    SUPS = "¹²³⁰⁴⁵⁶⁷⁸⁹"
    # Lines that are section headers or metadata inside the authors
    # blob, not names to keep.
    SKIP_PREFIXES = (
        "authors:", "author:", "corresponding", "affiliations:",
        "affiliation:", "presenting", "note:", "notes:",
    )
    # Institution keywords — if a line's leading word is one of these,
    # treat the whole line as an affiliation continuation, not a name.
    INSTITUTION_WORDS = (
        "university", "institute", "hospital", "college", "school",
        "department", "laboratory", "center", "centre", "program",
        "graduate",
    )

    lines: list[str] = []
    for chunk in raw.replace("\t", "\n").split("\n"):
        chunk = chunk.strip().strip(";").strip(",").strip()
        # Strip any leading bullet glyph + whitespace before the name.
        while chunk and chunk[0] in BULLETS:
            chunk = chunk[1:].lstrip()
        if not chunk:
            continue
        # Skip section headers / affiliation blocks.
        low = chunk.lower()
        if low.startswith(SKIP_PREFIXES):
            continue
        if chunk[0] in SUPS:
            continue
        if "@" in chunk:  # email / contact line
            continue
        first_word = low.split(maxsplit=1)[0].rstrip(",.:")
        if first_word in INSTITUTION_WORDS:
            continue
        lines.append(chunk)

    def _clean(nm: str) -> str:
        nm = nm.rstrip("*").rstrip(SUPS).strip()
        # Title-case names submitted entirely in lowercase (e.g. A017).
        # Skip if the string already mixes cases — we don't want to
        # clobber "de Silva" or "van der Berg" style names.
        if nm and nm == nm.lower() and any(c.isalpha() for c in nm):
            nm = " ".join(w.capitalize() for w in nm.split())
        return nm

    names: list[str] = []
    presenter_idx: int | None = None
    for ln in lines:
        # If the line carries superscript markers (¹²³ etc.), commas are
        # author separators, not name/affiliation separators. Split each
        # marker-bearing name off, strip the marker, keep going.
        if any(c in SUPS for c in ln) and "," in ln:
            parts = [p.strip() for p in ln.split(",") if p.strip()]
            for p in parts:
                if "*" in p and presenter_idx is None:
                    presenter_idx = len(names)
                nm = _clean(p)
                if nm and nm not in names:
                    names.append(nm)
            continue
        # Otherwise take the leading name portion before the first
        # affiliation separator.
        seg = ln
        for sep in (" — ", " – ", " - ", " (", ","):
            if sep in seg:
                seg = seg.split(sep, 1)[0]
                break
        if "*" in seg and presenter_idx is None:
            presenter_idx = len(names)
        nm = _clean(seg)
        if nm and nm not in names:
            names.append(nm)
    # Move the presenting author to the head of the list so
    # presenter_name() picks them.
    if presenter_idx is not None and 0 <= presenter_idx < len(names):
        names.insert(0, names.pop(presenter_idx))
    return names


def author_list(raw: str) -> str:
    return ", ".join(_split_authors(raw))


def presenter_name(raw: str) -> str:
    names = _split_authors(raw)
    return names[0] if names else "(presenter TBD)"


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------

def render_cover() -> list[str]:
    # Flyer image is committed as a tracked JPEG under static/img/. Typst
    # is invoked with --root <repo_root>, so leading-slash paths resolve
    # relative to the repo root.
    return [
        "# NECB 2026",
        "",
        "![](/static/img/flyer.jpg){width=6.5in}",
        "",
        "*Conference program & abstract book*",
        "",
        "---",
        "",
        (
            "This book contains the full two-day program — keynote and "
            "invited speaker biographies, all 22 selected talk abstracts, "
            "and every accepted poster abstract. Selected talks are listed "
            "in program order; posters are indexed by abstract id, which "
            "will match the physical board number in the poster hall."
        ),
        "",
        (
            "Presenting authors: please refer to the acceptance email you "
            "received on Fri Sep 4, 2026 for logistics and slot assignment. "
            "For any corrections, contact "
            "`newenglandcompbio@gmail.com`."
        ),
        "",
    ]


def render_schedule(program) -> list[str]:
    md: list[str] = ["# Program at a Glance", ""]
    for day in program["days"]:
        md += [f"## {day['label']}", ""]
        for sess in day["sessions"]:
            md += [f"### {sess['time']} · {sess['title']}", ""]
            for name in sess.get("speakers") or []:
                md.append(f"- **{name}**")
            for t in sess.get("talks") or []:
                aid = t["abstract_id"]
                md.append(
                    f"- **{aid}** · {t['title']}  "
                    f"\n  {t['presenter']} · {t['affiliation']}"
                )
            md.append("")
    return md


def _typst_escape(s: str) -> str:
    """Escape a plain-text field for embedding inside a typst string
    literal (used in raw {=typst} blocks for speaker cards)."""
    return s.replace("\\", "\\\\").replace("\"", "\\\"")


def _speaker_bio_page(m: dict) -> list[str]:
    """Emit one speaker card as a raw typst block using the template's
    #speaker-card helper (photo-left, name/affiliation/bio-right)."""
    photo = m.get("photo")
    photo_arg = f"\"/static/{photo}\"" if photo else "none"
    name = _typst_escape(m.get("name", ""))
    aff = _typst_escape(m.get("affiliation", ""))
    bio = (m.get("bio", "") or "").strip()
    # Bio text inside a typst content block [...] — escape any '#' or
    # bracket characters that would otherwise be parsed as markup.
    bio_body = (
        bio.replace("\\", "\\\\")
           .replace("[", "\\[")
           .replace("]", "\\]")
           .replace("#", "\\#")
    )
    return [
        "```{=typst}",
        (
            f"#speaker-card(photo: {photo_arg}, name: \"{name}\", "
            f"affiliation: \"{aff}\", bio: ["
        ),
        bio_body,
        "])",
        "```",
        "",
    ]


def render_keynote_bios(speakers) -> list[str]:
    md = ["# Keynote Speakers", ""]
    for m in speakers["keynotes"]["members"]:
        md += _speaker_bio_page(m)
    return md


def render_invited_bios(speakers) -> list[str]:
    md = ["# Invited Speakers", ""]
    for m in speakers["invited"]["members"]:
        md += _speaker_bio_page(m)
    return md


def render_abstract(aid: str, sub: dict, session_label: str | None = None) -> list[str]:
    # Every abstract starts on its own page. The template's H3 rule is
    # shared with the schedule H3s (which should not pagebreak), so we
    # emit an explicit typst pagebreak here rather than folding it into
    # the H3 show rule.
    md: list[str] = [
        "```{=typst}",
        "#pagebreak(weak: true)",
        "```",
        "",
        f"### {aid} · {sub['title']}",
        "",
    ]
    md.append(f"**Presenter:** {presenter_name(sub['authors'])} — {sub['affiliation']}")
    md.append("")
    md.append(f"**Authors:** {author_list(sub['authors'])}")
    md.append("")
    if session_label:
        md.append(f"**Session:** {session_label}")
        md.append("")
    md.append(sub["abstract"])
    md.append("")
    return md


def render_talks(program, subs) -> tuple[list[str], list[str]]:
    """Return (markdown_lines, missing_ids)."""
    md: list[str] = ["# Selected Talks · Abstracts", ""]
    missing: list[str] = []
    for day in program["days"]:
        for sess in day["sessions"]:
            for t in sess.get("talks") or []:
                aid = t["abstract_id"]
                sub = subs.get(aid)
                if sub is None:
                    missing.append(aid)
                    continue
                session_label = f"{day['label']} · {sess['time']}"
                md += render_abstract(aid, sub, session_label)
    return md, missing


def render_posters(poster_ids, subs, day_map) -> tuple[list[str], list[str]]:
    md: list[str] = ["# Poster Presentations · Abstracts", ""]
    missing: list[str] = []
    # Split by day when available (day_map from posterSessions.yaml); each
    # day still splits into regular / late-breaking so late-breaking rows
    # get a visible section header.
    unknown = [aid for aid in poster_ids if aid not in subs]
    missing.extend(unknown)

    if day_map:
        # Group by day label preserving posterSessions.yaml order
        day_buckets: dict[str, list[str]] = {}
        for aid in poster_ids:
            if aid not in subs:
                continue
            label = day_map.get(aid, ("Unassigned", ""))[0]
            day_buckets.setdefault(label, []).append(aid)
        for label, ids in day_buckets.items():
            md += [f"## {label}", ""]
            reg = [aid for aid in ids if subs[aid].get("round") == "regular"]
            late = [aid for aid in ids if subs[aid].get("round") == "late-breaking"]
            if reg:
                md += ["### Regular round", ""]
                for aid in sorted(reg):
                    time = day_map.get(aid, ("", ""))[1]
                    session_label = f"{label} · {time}" if time else label
                    md += render_abstract(aid, subs[aid], session_label)
            if late:
                md += ["### Late-breaking", ""]
                for aid in sorted(late):
                    time = day_map.get(aid, ("", ""))[1]
                    session_label = f"{label} · {time}" if time else label
                    md += render_abstract(aid, subs[aid], session_label)
    else:
        regular = sorted(aid for aid in poster_ids if subs.get(aid, {}).get("round") == "regular")
        late = sorted(aid for aid in poster_ids if subs.get(aid, {}).get("round") == "late-breaking")
        if regular:
            md += ["## Regular round", ""]
            for aid in regular:
                md += render_abstract(aid, subs[aid])
        if late:
            md += ["## Late-breaking", ""]
            for aid in late:
                md += render_abstract(aid, subs[aid])
    return md, missing


def render_organizers(orgs) -> list[str]:
    """Render the committee back-matter using each group's yaml-supplied
    `title`. Iterate in the order they appear in organizers.yaml so the
    file stays the source of truth for ordering.

    'friends' and 'reviewers' render as a compact comma-joined line each
    (they're long and don't need per-line formatting)."""
    md = ["# Organizing Committee", ""]
    COMPACT = {"friends", "reviewers"}
    for key, group in orgs.items():
        if not isinstance(group, dict) or "members" not in group:
            continue
        title = group.get("title") or key.replace("_", " ").title()
        md.append(f"## {title}")
        md.append("")
        intro = group.get("intro")
        if intro:
            md.append(intro.strip())
            md.append("")
        if key in COMPACT:
            names = [
                f"{m.get('name', '')}"
                + (f" ({m['affiliation']})" if m.get("affiliation") else "")
                for m in group["members"]
                if m.get("name")
            ]
            md.append(", ".join(names) + ".")
        else:
            for m in group["members"]:
                line = f"- **{m.get('name', '')}**"
                role = m.get("role")
                aff = m.get("affiliation")
                if role:
                    line += f" — {role}"
                if aff:
                    line += f", *{aff}*"
                md.append(line)
        md.append("")
    return md


def render_code_of_conduct() -> list[str]:
    return [
        "# Code of Conduct",
        "",
        (
            "NECB 2026 follows the "
            "[ISCB Code of Conduct](https://www.iscb.org/iscb-policy-statements/iscb-code-conduct). "
            "We are committed to a respectful, inclusive symposium and expect "
            "all participants — attendees, speakers, sponsors, and organizers — "
            "to help maintain that environment throughout the meeting."
        ),
        "",
        (
            "Harassment, discrimination, and disrespectful behaviour of any "
            "kind are not welcome, in-person or online. Please report any "
            "concerns to the organizing committee at "
            "`newenglandcompbio@gmail.com`, or to any of the co-chairs in "
            "person."
        ),
        "",
    ]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    program = load_yaml("program.yaml")
    speakers = load_yaml("speakers.yaml")
    orgs = load_yaml("organizers.yaml")
    subs = load_submissions()
    withdrawn = load_withdrawn_ids()  # includes talk + poster withdrawals
    poster_ids = [aid for aid in load_poster_ids() if aid not in withdrawn]
    poster_day_map = load_poster_day_map()

    # Talks: program.yaml is the source of truth (any withdrawn talk is
    # already removed from it; conversely A185 Lenore Cowen was
    # 'poster-withdrawn' because she was promoted from poster to talk,
    # so we do NOT filter talks against the withdrawals set).
    talk_ids = [
        t["abstract_id"]
        for day in program["days"]
        for sess in day["sessions"]
        for t in (sess.get("talks") or [])
    ]

    lines: list[str] = []
    lines += render_cover()
    lines += render_schedule(program)
    lines += render_keynote_bios(speakers)
    lines += render_invited_bios(speakers)
    talks_md, talks_missing = render_talks(program, subs)
    lines += talks_md
    if poster_ids:
        posters_md, posters_missing = render_posters(poster_ids, subs, poster_day_map)
        lines += posters_md
    else:
        posters_missing = []
        print(
            "warning: no poster source (data/posterSessions.yaml or "
            "docs/review/build/decisions_posters.csv) — skipping posters.",
            file=sys.stderr,
        )
    lines += render_organizers(orgs)
    lines += render_code_of_conduct()

    OUT.write_text("\n".join(lines) + "\n")

    # Summary + orphan report
    n_reg = sum(1 for aid in poster_ids if subs.get(aid, {}).get("round") == "regular")
    n_late = sum(1 for aid in poster_ids if subs.get(aid, {}).get("round") == "late-breaking")
    total_abstracts = len(talk_ids) + len(poster_ids)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  Talks:               {len(talk_ids)}")
    print(f"  Posters (regular):   {n_reg}")
    print(f"  Posters (late):      {n_late}")
    print(f"  Total abstracts:     {total_abstracts}")
    print(f"  Keynote bios:        {len(speakers['keynotes']['members'])}")
    print(f"  Invited bios:        {len(speakers['invited']['members'])}")

    orphans = talks_missing + posters_missing
    if orphans:
        print(
            f"\nERROR: {len(orphans)} abstract id(s) referenced in the program "
            f"or accepted-poster list have no matching row in the submissions "
            f"CSVs:",
            file=sys.stderr,
        )
        for aid in orphans:
            print(f"  {aid}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
