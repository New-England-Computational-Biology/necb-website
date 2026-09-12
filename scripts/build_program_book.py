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


def load_poster_presenter_map() -> dict[str, tuple[str, str]]:
    """Map abstract_id -> (presenter_name, affiliation) for accepted
    posters. Used as a fallback when the submissions CSV has an empty
    authors field (see A171)."""
    if not POSTER_SESSIONS.exists():
        return {}
    y = yaml.safe_load(POSTER_SESSIONS.read_text())
    m: dict[str, tuple[str, str]] = {}
    for day in y.get("days", []):
        for p in day.get("posters", []):
            aid = p.get("abstract_id", "").strip()
            if aid:
                m[aid] = (
                    p.get("presenter", "").strip(),
                    p.get("affiliation", "").strip(),
                )
    return m


def load_talk_presenter_map(program) -> dict[str, tuple[str, str]]:
    """Map abstract_id -> (presenter_name, affiliation) for talks in
    the schedule (program.yaml)."""
    m: dict[str, tuple[str, str]] = {}
    for day in program["days"]:
        for sess in day["sessions"]:
            for t in (sess.get("talks") or []):
                aid = t.get("abstract_id", "").strip()
                if aid:
                    m[aid] = (
                        t.get("presenter", "").strip(),
                        t.get("affiliation", "").strip(),
                    )
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
    # blob, not names to keep. Matched with and without trailing ':'.
    SKIP_HEADINGS = {
        "authors", "author", "corresponding", "corresponding author",
        "affiliations", "affiliation", "presenting", "presenting author",
        "note", "notes", "to whom",
    }
    # Institution keywords — if a line's leading word is one of these,
    # treat the whole line as an affiliation continuation, not a name.
    INSTITUTION_WORDS = (
        "university", "institute", "hospital", "college", "school",
        "department", "laboratory", "center", "centre", "program",
        "graduate", "faculty", "division", "clinic", "section",
        "national", "harvard", "hms", "mit", "stanford", "yale",
        "columbia", "cornell", "duke", "bioinformatics",
        "licenciatura",  # A024 specifically has this in a Spanish institution
    )
    # 'Name (1,2)' style affiliation markers — remove the whole
    # parenthesized numeric group so the authors on the line survive
    # via a plain comma split (see A041: 'Andrew Chen (1,2), Stefano
    # Monti (1,2,3)').
    NUM_PAREN = _re.compile(r"\s*\(\s*\d+(?:\s*[,\s]\s*\d+)*\s*\)")
    # Parenthesized role notes tacked onto a name — 'Name — Affil (co-
    # corresp.)' etc. Strip them so downstream separator splitting
    # doesn't lock onto ' (' first and steal the whole affiliation.
    ROLE_PAREN = _re.compile(
        r"\s*\(\s*(?:co-?corresp(?:onding)?\.?|corresp(?:onding)?\.?|"
        r"co-?first(?:\s+author)?|first\s+author|equal\s+contribution|"
        r"presenting(?:\s+author)?|senior(?:\s+author)?|lead(?:\s+author)?"
        r")\s*\)",
        _re.I,
    )

    # Strip leading '1. ', '2. ', '10. ' style enumerator prefixes from
    # numbered author lists (see A088: '1. Arif Ahmad Rather - Dept…').
    ENUM_PREFIX = _re.compile(r"^\d+[.\)]\s+")

    lines: list[str] = []
    for chunk in raw.replace("\t", "\n").split("\n"):
        chunk = chunk.strip().strip(";").strip(",").strip()
        # Strip any leading bullet glyph + whitespace before the name.
        while chunk and chunk[0] in BULLETS:
            chunk = chunk[1:].lstrip()
        # Strip '1. ' / '2. ' / '1) ' enumerator prefixes so a numbered
        # author list survives; must run *before* the digit-leading skip.
        m = ENUM_PREFIX.match(chunk)
        if m:
            chunk = chunk[m.end():]
        if not chunk:
            continue
        # Skip section headers / affiliation blocks (matched bare or with
        # trailing colon).
        low = chunk.lower().rstrip(":").strip()
        if low in SKIP_HEADINGS or low + ":" in SKIP_HEADINGS:
            continue
        # Strip 'Name — Affil (co-corresp.)' style role notes first so
        # the ' (' separator doesn't fire on them.
        chunk = ROLE_PAREN.sub("", chunk)
        # Strip 'Name (1,2)' style numeric-affiliation markers so downstream
        # comma-splitting yields individual authors instead of tangling
        # the marker into a name. Remember if any were stripped — that
        # signals commas on the line are author separators, not
        # name/affiliation separators (same logic as the SUPS branch).
        new_chunk, sub_count = NUM_PAREN.subn("", chunk)
        chunk = new_chunk.strip().strip(";").strip(",").strip()
        if sub_count and chunk:
            chunk = " __NUMPAREN__" + chunk  # marker keyed off later
        if not chunk:
            continue
        low = chunk.lower()
        if chunk[0] in SUPS:
            continue
        if "@" in chunk:  # email / contact line
            continue
        # Skip lines that start with a digit — those are ASCII-numbered
        # affiliation continuations (e.g. '1 McLean Hospital',
        # '1Center for Theoretical Biological Physics'). Numbered-author
        # prefixes were already trimmed above.
        if chunk[0].isdigit():
            continue
        first_word = low.split(maxsplit=1)[0].rstrip(",.:")
        if first_word in INSTITUTION_WORDS:
            continue
        lines.append(chunk)

    # Honorifics we strip from the front of a name — 'Dr.', 'Prof.',
    # 'Mr.', 'Ms.', 'Mrs.', 'Miss'. Matched with a trailing dot or space.
    TITLES = (
        "dr.", "dr", "prof.", "prof", "professor",
        "mr.", "mr", "ms.", "ms", "mrs.", "mrs", "miss",
    )

    # Trailing ASCII digit-group affiliation markers ('Yukai You1',
    # 'Aarti Jajoo * 1,2,3', 'Name1,2'). Strip everything after the last
    # letter that looks like a marker string.
    TAIL_MARKER = _re.compile(r"[\s*]*\d[\d,\s*]*$")
    # Some authors use 'Name-Word Word ...' with no spaces around the
    # dash to attach an institution (A199: 'Fowler-Department of Genome
    # Sciences'). If the name still carries such a tail after the sep
    # split, strip everything from the dash on. Only fires when the
    # dash is followed by a Latin word-character run that looks like an
    # institution keyword; leaves 'Chi-Ping', 'Maria-Elena' alone.
    INSTITUTION_KEYWORDS_RE = _re.compile(
        r"[-](Department|Center|Centre|Division|Faculty|Institute|"
        r"School|College|University|Laboratory|Program|Hospital|"
        r"National|Broad|Harvard|MIT|Yale|Stanford|Columbia|Duke)\b"
    )

    def _clean(nm: str) -> str:
        nm = nm.rstrip("*").rstrip(SUPS).strip()
        # Strip ASCII digit markers at the end of the name.
        nm = TAIL_MARKER.sub("", nm).strip()
        nm = nm.rstrip("*").rstrip(",").strip()
        # Snip any 'Name-InstitutionKeyword…' tail.
        m = INSTITUTION_KEYWORDS_RE.search(nm)
        if m:
            nm = nm[:m.start()].rstrip()
        # Strip honorific title prefixes (A182: "Dr. Amanda Storm").
        parts = nm.split()
        if parts and parts[0].lower() in TITLES:
            nm = " ".join(parts[1:]).strip()
        # Title-case names submitted entirely in lowercase (e.g. A017).
        # Skip if the string already mixes cases — we don't want to
        # clobber "de Silva" or "van der Berg" style names.
        if nm and nm == nm.lower() and any(c.isalpha() for c in nm):
            nm = " ".join(w.capitalize() for w in nm.split())
        return nm

    names: list[str] = []
    presenter_idx: int | None = None
    for ln in lines:
        # Numeric-affiliation-marker lines (removed markers left a
        # __NUMPAREN__ sentinel): treat commas as author separators.
        if ln.startswith(" __NUMPAREN__"):
            ln = ln[len(" __NUMPAREN__"):].strip()
            parts = [p.strip() for p in ln.split(",") if p.strip()]
            for p in parts:
                if "*" in p and presenter_idx is None:
                    presenter_idx = len(names)
                nm = _clean(p)
                if nm and nm not in names:
                    names.append(nm)
            continue
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
        for sep in (" (", " — ", " – ", " -- ", " - ", " : ", ":", "- ", "; ", ";", ","):
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

def render_toc() -> list[str]:
    """Two-level table of contents built by typst from the H1/H2 headings
    already in the document. Landing on its own page just after the
    cover keeps the front-matter tidy."""
    return [
        "```{=typst}",
        "#pagebreak(weak: true)",
        "#block(above: 0pt, below: 16pt)[",
        "  #set text(font: \"Avenir Next\", size: 18pt, weight: 700, fill: c-fuchsia)",
        "  Contents",
        "  #v(6pt, weak: true)",
        "  #line(length: 100%, stroke: 1.8pt + c-fuchsia)",
        "]",
        "#outline(",
        "  title: none,",
        "  depth: 2,",
        "  indent: 1em,",
        ")",
        "```",
        "",
    ]


def render_cover() -> list[str]:
    """Minimal cover for now — a wordmark title, subtitle, dates, and
    venue. Kept text-only until we have a proper cover asset.

    Followed by a Welcome page (H1) with the co-chair message on its
    own page so the cover reads as a clean title sheet.
    """
    return [
        # Modeled on the hero section at the top of the website:
        # small teal eyebrow, big three-line fuchsia wordmark title
        # (the year lives on its own line, no year separator), a navy
        # meta line with the dates + venue, and a short pitch.
        "```{=typst}",
        "#v(1.4in)",
        "#align(left)[",
        "  // eyebrow",
        "  #block[",
        "    #box(fill: c-fuchsia, radius: 999pt, width: 0.35em, "
        "height: 0.35em, [])",
        "    #h(0.4em)",
        "    #text(font: \"Avenir Next\", size: 9pt, weight: 600, fill: c-teal, "
        "tracking: 1pt)[",
        "      #upper[Inaugural Symposium · Cambridge, MA]",
        "    ]",
        "  ]",
        "  #v(10pt)",
        "  // title stack",
        "  #text(font: \"Avenir Next\", size: 38pt, weight: 700, fill: c-fuchsia)[",
        "    New England \\",
        "    Computational \\",
        "    Biology  ",
        "    #text(size: 32pt, fill: c-navy)[2026]",
        "  ]",
        "  #v(14pt)",
        "  // meta",
        "  #text(font: \"Avenir Next\", size: 11pt, weight: 600, fill: c-navy)[",
        "    October 1–2, 2026",
        "  ]",
        "  #text(font: \"Avenir Next\", size: 11pt, fill: c-muted)[",
        "    #h(0.3em) · #h(0.3em) Microsoft Research New England",
        "  ]",
        "  #v(20pt)",
        "  // pitch",
        "  #block(width: 4in)[",
        "    #set text(font: \"Charter\", size: 10.5pt, fill: c-ink)",
        "    #set par(leading: 0.6em, justify: false)",
        "    Two days of talks, posters, and conversations at the frontier of "
        "computation and the life sciences, hosted by Microsoft Research "
        "New England in Cambridge, MA.",
        "  ]",
        "]",
        "#pagebreak(weak: true)",
        "```",
        "",
        "# Welcome",
        "",
        (
            "Welcome to the **New England Computational Biology Symposium 2026**. "
            "We are delighted to bring together researchers, students, and "
            "practitioners from across the region for two days of talks, "
            "posters, and conversations at the intersection of computation and "
            "biology."
        ),
        "",
        (
            "This year's program features **5 keynote speakers**, **6 invited "
            "talks**, **23 selected talks**, and **180 poster presentations**, "
            "chosen from a large and exceptional pool of submissions. Sessions "
            "span single-cell and spatial biology, protein design and function, "
            "genomics and regulation, immunology and vaccines, clinical and "
            "translational applications, and AI methods and applications."
        ),
        "",
        (
            "We are grateful to our sponsors, our host at Microsoft Research "
            "New England, ISCB for coordinating registration and logistics, "
            "and the many volunteer reviewers who made the selection process "
            "possible. Above all, thank you for joining us."
        ),
        "",
        "*Luca Pinello, Predrag Radivojac, and Kevin Yang*  ",
        "*Conference Co-Chairs, NECB 2026*",
        "",
    ]


def _typ(s: str) -> str:
    """Escape a plain-text field for embedding inside a typst content
    block [ ... ] via a raw {=typst} pass-through."""
    return (s.replace("\\", "\\\\")
             .replace("[", "\\[").replace("]", "\\]")
             .replace("#", "\\#").replace("@", "\\@")
             .replace("<", "\\<").replace(">", "\\>"))


def render_schedule(program) -> list[str]:
    md: list[str] = ["# Program at a Glance", ""]
    for day in program["days"]:
        md += [f"## {day['label']}", ""]
        for sess in day["sessions"]:
            md += [f"### {sess['time']} · {sess['title']}", ""]
            speakers = sess.get("speakers") or []
            talks = sess.get("talks") or []
            if speakers:
                # Same grid geometry as the talks stanza below so keynote
                # and invited speaker names line up with talk titles
                # (empty ID column on the left, name on the right).
                md.append("```{=typst}")
                for name in speakers:
                    md.append(
                        "#block(above: 5pt, below: 5pt, breakable: false)["
                        "#grid(columns: (0.4in, 1fr), column-gutter: 6pt, "
                        "align: (right + top, left + top), "
                        "[], "
                        f"[#text(weight: 600)[{_typ(name)}]])]"
                    )
                md.append("```")
                md.append("")
            if talks:
                md.append("```{=typst}")
                for t in talks:
                    aid = _typ(t["abstract_id"])
                    title = _typ(t["title"])
                    presenter = _typ(t.get("presenter", ""))
                    affil = _typ(t.get("affiliation", ""))
                    md.append(
                        "#block(above: 5pt, below: 5pt, breakable: false)["
                        "#grid(columns: (0.4in, 1fr), column-gutter: 6pt, "
                        "align: (right + top, left + top), "
                        "[#text(font: \"Menlo\", size: 8pt, fill: c-fuchsia, "
                        f"weight: 600)[{aid}]], "
                        f"[#text(weight: 600)[{title}]\\ "
                        "#text(size: 0.85em, fill: c-muted)["
                        f"{presenter} · {affil}]])]"
                    )
                md.append("```")
                md.append("")
            md.append("")
    return md


def _typst_escape(s: str) -> str:
    """Escape a plain-text field for embedding inside a typst string
    literal (used in raw {=typst} blocks for speaker cards)."""
    return s.replace("\\", "\\\\").replace("\"", "\\\"")


def _condense_bio(bio: str, max_chars: int = 320) -> str:
    """Trim a bio to roughly max_chars, breaking at the end of the
    sentence closest to the target length. Used for the compact
    speaker-grid layout so all keynotes/invited speakers share a page."""
    bio = " ".join((bio or "").split())
    if len(bio) <= max_chars:
        return bio
    cut = bio[:max_chars]
    dot = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if dot > max_chars * 0.5:
        return cut[: dot + 1]
    space = cut.rfind(" ")
    return cut[:space] + "…" if space > 0 else cut + "…"


def _speaker_mini_call(m: dict, max_chars: int = 320) -> str:
    """Return one typst `speaker-mini(...)` call string. Used as a cell
    in the two-column keynote / invited page grid."""
    photo = m.get("photo")
    photo_arg = f"\"/static/{photo}\"" if photo else "none"
    name = _typst_escape(m.get("name", ""))
    aff = _typst_escape(m.get("affiliation", ""))
    bio = _condense_bio(m.get("bio", ""), max_chars)
    bio_body = (
        bio.replace("\\", "\\\\")
           .replace("[", "\\[")
           .replace("]", "\\]")
           .replace("#", "\\#")
    )
    return (
        f"speaker-mini(photo: {photo_arg}, name: \"{name}\", "
        f"affiliation: \"{aff}\", bio: [{bio_body}])"
    )


def _speaker_page(part_title: str, members: list[dict], max_chars: int) -> list[str]:
    """One-page compact grid of speaker mini-cards under a part heading."""
    md = [f"# {part_title}", ""]
    cards = ", ".join(_speaker_mini_call(m, max_chars) for m in members)
    md += [
        "```{=typst}",
        f"#speaker-grid(({cards},))",
        "```",
        "",
    ]
    return md


def render_keynote_bios(speakers) -> list[str]:
    # 5 keynote speakers in a 2-column x 3-row grid (the last row
    # carries a single card). Bios trimmed short enough that Zhiping
    # (the 5th) still lands on the same page as the other four.
    return _speaker_page(
        "Keynote Speakers", speakers["keynotes"]["members"], max_chars=220,
    )


def render_invited_bios(speakers) -> list[str]:
    # 6 invited speakers → exact 2 x 3 grid.
    return _speaker_page(
        "Invited Speakers", speakers["invited"]["members"], max_chars=220,
    )


def render_abstract(aid: str, sub: dict, session_label: str | None = None,
                    presenter_hint: tuple[str, str] | None = None,
                    stick_to_prev: bool = False) -> list[str]:
    # Every subsequent abstract starts on its own page. `stick_to_prev`
    # is set True by callers immediately after a part heading or round
    # banner, so the first abstract there fits right underneath the
    # heading/banner rather than getting pushed onto a fresh page.
    md: list[str] = []
    if not stick_to_prev:
        md += [
            "```{=typst}",
            "#pagebreak(weak: true)",
            "```",
            "",
        ]
    md += [
        f"### {aid} · {sub['title']}",
        "",
    ]
    # Presenter line — prefer the curated map (program.yaml /
    # posterSessions.yaml) for the *name*, but prefer the CSV
    # presenting_affiliation for the *affiliation* since the program
    # book has room to spell things out and the map's affiliation is
    # tuned for the compact website (e.g. 'BCH · HMS'). Author list
    # still comes from the CSV so co-authors are preserved.
    author_field = (sub.get("authors") or "").strip()
    csv_affil = (sub.get("affiliation") or "").strip()
    if presenter_hint and presenter_hint[0]:
        presenter, hint_affil = presenter_hint
        affil = csv_affil or hint_affil
        md.append(f"**Presenter:** {presenter} — {affil}")
    else:
        presenter = presenter_name(sub["authors"]) if author_field else "(presenter TBD)"
        md.append(f"**Presenter:** {presenter} — {csv_affil}")
    md.append("")
    if author_field:
        md.append(f"**Authors:** {author_list(author_field)}")
    elif presenter_hint and presenter_hint[0]:
        md.append(f"**Authors:** {presenter_hint[0]}")
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
    first = True
    for day in program["days"]:
        for sess in day["sessions"]:
            for t in sess.get("talks") or []:
                aid = t["abstract_id"]
                sub = subs.get(aid)
                if sub is None:
                    missing.append(aid)
                    continue
                session_label = f"{day['label']} · {sess['time']}"
                presenter_hint = (
                    (t.get("presenter") or "").strip(),
                    (t.get("affiliation") or "").strip(),
                )
                md += render_abstract(
                    aid, sub, session_label, presenter_hint,
                    stick_to_prev=first,
                )
                first = False
    return md, missing


def render_posters(poster_ids, subs, day_map,
                   presenter_map: dict[str, tuple[str, str]] | None = None
                   ) -> tuple[list[str], list[str]]:
    md: list[str] = ["# Poster Presentations · Abstracts", ""]
    missing: list[str] = []
    presenter_map = presenter_map or {}
    # Split by day when available (day_map from posterSessions.yaml); each
    # day still splits into regular / late-breaking so late-breaking rows
    # get a visible section header.
    unknown = [aid for aid in poster_ids if aid not in subs]
    missing.extend(unknown)

    def hint(aid: str) -> tuple[str, str] | None:
        return presenter_map.get(aid)

    if day_map:
        # Group by day label preserving posterSessions.yaml order
        day_buckets: dict[str, list[str]] = {}
        for aid in poster_ids:
            if aid not in subs:
                continue
            label = day_map.get(aid, ("Unassigned", ""))[0]
            day_buckets.setdefault(label, []).append(aid)
        first_day = True
        for label, ids in day_buckets.items():
            # First day flows right under the H1 'Poster Presentations
            # · Abstracts' heading (no pagebreak); subsequent days start
            # a fresh page.
            pb = "false" if first_day else "true"
            md += [
                "```{=typst}",
                f"#day-banner([{label}], page_break: {pb})",
                "```",
                "",
            ]
            first_day = False
            reg = [aid for aid in ids if subs[aid].get("round") == "regular"]
            late = [aid for aid in ids if subs[aid].get("round") == "late-breaking"]
            if reg:
                # First round in the day flows right under the day
                # banner (no pagebreak); the first abstract of the
                # round then also sticks under the round banner.
                md += _round_banner("Regular round", force_break=False)
                for i, aid in enumerate(sorted(reg)):
                    time = day_map.get(aid, ("", ""))[1]
                    session_label = f"{label} · {time}" if time else label
                    md += render_abstract(
                        aid, subs[aid], session_label, hint(aid),
                        stick_to_prev=(i == 0),
                    )
            if late:
                # Late-breaking always starts on a fresh page after the
                # last Regular-round abstract.
                md += _round_banner("Late-breaking", force_break=True)
                for i, aid in enumerate(sorted(late)):
                    time = day_map.get(aid, ("", ""))[1]
                    session_label = f"{label} · {time}" if time else label
                    md += render_abstract(
                        aid, subs[aid], session_label, hint(aid),
                        stick_to_prev=(i == 0),
                    )
    else:
        regular = sorted(aid for aid in poster_ids if subs.get(aid, {}).get("round") == "regular")
        late = sorted(aid for aid in poster_ids if subs.get(aid, {}).get("round") == "late-breaking")
        if regular:
            md += _round_banner("Regular round")
            for aid in regular:
                md += render_abstract(aid, subs[aid], presenter_hint=hint(aid))
        if late:
            md += _round_banner("Late-breaking")
            for aid in late:
                md += render_abstract(aid, subs[aid], presenter_hint=hint(aid))
    return md, missing


def _round_banner(label: str, force_break: bool = False) -> list[str]:
    """Compact section separator between round groups inside a day —
    renders as a small navy uppercase banner in the typst template, not
    as another heading level, so it doesn't compete visually with the
    day (H2) or the abstract entries (H3). By default lets the banner
    flow inline (so the first-in-day round can share the day banner's
    page); set force_break=True for subsequent rounds within a day
    (e.g. Late-breaking after Regular round).
    """
    lines = ["```{=typst}"]
    if force_break:
        lines.append("#pagebreak(weak: true)")
    lines += [
        "#block(above: 12pt, below: 10pt)[",
        "  #set text(font: \"Avenir Next\", size: 10pt, weight: 700,",
        "    fill: c-navy, tracking: 1.5pt)",
        f"  #upper[{label}]",
        "  #v(-3pt, weak: true)",
        "  #line(length: 100%, stroke: 0.5pt + c-navy)",
        "]",
        "```",
        "",
    ]
    return lines


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
        # H3 so committee subsections don't clutter the outline (which
        # caps at depth 2). Visually still bold navy via the H3 rule.
        md.append(f"### {title}")
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
    lines += render_toc()
    lines += render_schedule(program)
    lines += render_keynote_bios(speakers)
    lines += render_invited_bios(speakers)
    talks_md, talks_missing = render_talks(program, subs)
    lines += talks_md
    if poster_ids:
        poster_presenter_map = load_poster_presenter_map()
        posters_md, posters_missing = render_posters(
            poster_ids, subs, poster_day_map, poster_presenter_map,
        )
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
