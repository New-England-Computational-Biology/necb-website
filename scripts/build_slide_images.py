#!/usr/bin/env python3
"""Build 16:9 headshot slides (1920 x 1080) for the opening remarks.

Same look as the social cards in build_social_images.py (navy heading,
gold rule, circular headshots) but sized for slides and without the
social footer. One slide per group: keynote and invited speakers
(data/speakers.yaml) and the co-chairs, steering and organizing
committees (data/organizers.yaml).

People without a photo get an initials disc in a brand colour. To use a
real headshot, save it as static/img/people/<first-last>.jpg (square
crop, face centred) and re-run; the file is picked up automatically.

Output: docs/slides/*.png

Usage:
    python3 scripts/build_slide_images.py
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PEOPLE = ROOT / "static" / "img" / "people"
MARK = ROOT / "docs" / "print" / "logo" / "necb-mark.png"
OUT = ROOT / "docs" / "slides"
FONTS = ROOT / "docs" / "print" / "banners" / "fonts"

W, H = 1920, 1080
FUCHSIA, NAVY, TEAL = (179, 23, 77), (39, 61, 145), (15, 90, 87)
MUTED, GOLD, WHITE = (91, 95, 107), (213, 138, 25), (255, 255, 255)
DISC = [NAVY, TEAL, FUCHSIA, (143, 26, 62)]


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Arimo-{'Bold' if bold else 'Regular'}.ttf"), size)


def slug(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", "-", name).strip("-")


def photo_for(member: dict) -> Path | None:
    if member.get("photo"):
        p = ROOT / "static" / member["photo"]
        if p.exists():
            return p
    for ext in (".jpg", ".jpeg", ".png"):
        p = PEOPLE / f"{slug(member['name'])}{ext}"
        if p.exists():
            return p
    return None


def disc(member: dict, size: int, i: int) -> Image.Image:
    """Circular headshot, or an initials disc when there is no photo."""
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    p = photo_for(member)
    if p:
        ph = Image.open(p).convert("RGB")
        s = min(ph.size)  # centre-crop to square
        ph = ph.crop(((ph.width - s) // 2, (ph.height - s) // 2,
                      (ph.width + s) // 2, (ph.height + s) // 2)).resize((size, size), Image.LANCZOS)
    else:
        ph = Image.new("RGB", (size, size), DISC[i % len(DISC)])
        words = re.sub(r"\(.*?\)", "", member["name"]).split()
        initials = (words[0][0] + words[-1][0]).upper()
        d = ImageDraw.Draw(ph)
        f = font(int(size * 0.36))
        d.text((size / 2, size / 2), initials, font=f, fill=WHITE, anchor="mm")
    ph.putalpha(mask)
    return ph


def centered(d, cx, y, text, f, fill):
    d.text((cx - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def fit(d, text, f_size, max_w, bold=True):
    """Shrink the font until the line fits the column."""
    while f_size > 14 and d.textlength(text, font=font(f_size, bold)) > max_w:
        f_size -= 1
    return font(f_size, bold)


def slide(heading: str, people: list[tuple[dict, str]]) -> Image.Image:
    """people: (member, caption) pairs; caption is the fuchsia third line."""
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    mark = Image.open(MARK).convert("RGBA")
    mark = mark.resize((round(mark.width * 104 / mark.height), 104), Image.LANCZOS)
    im.paste(mark, (96, 48), mark)
    d.text((212, 72), heading, font=font(58), fill=NAVY)
    meta = "NECB 2026 · Oct 1–2 · Cambridge, MA"
    d.text((W - 96 - d.textlength(meta, font=font(32)), 90), meta, font=font(32), fill=FUCHSIA)
    d.line((96, 168, W - 96, 168), fill=GOLD, width=5)

    n = len(people)
    per_row = n if n <= 4 else (3 if n in (5, 6) else (4 if n <= 8 else 5))
    rows = [people[i:i + per_row] for i in range(0, n, per_row)]
    one_row = len(rows) == 1
    size = 380 if one_row else {3: 270, 4: 250}.get(per_row, 220)
    name_s, aff_s, cap_s = (44, 32, 30) if one_row else (34, 26, 25)
    text_h = name_s + aff_s + (cap_s if any(c for _, c in people) else 0) + 44
    gap = 40
    area_top, area_bottom = 196, H - 60
    block = len(rows) * (size + text_h) + (len(rows) - 1) * gap
    top = area_top + (area_bottom - area_top - block) // 2
    col_w = (W - 192) / per_row
    k = 0
    for r, row in enumerate(rows):
        # centre short rows
        x0 = 96 + (per_row - len(row)) * col_w / 2
        for c, (m, cap) in enumerate(row):
            cx = x0 + col_w * (c + 0.5)
            y = top + r * (size + text_h + gap)
            ph = disc(m, size, k); k += 1
            im.paste(ph, (int(cx - size / 2), y), ph)
            name = re.sub(r"\s*\(.*?\)", "", m["name"])
            ty = y + size + 18
            centered(d, cx, ty, name, fit(d, name, name_s, col_w - 16), NAVY)
            aff = m.get("short_affiliation") or m.get("affiliation", "")
            ty += name_s + 10
            centered(d, cx, ty, aff, fit(d, aff, aff_s, col_w - 16, bold=False), MUTED)
            if cap:
                centered(d, cx, ty + aff_s + 10, cap, fit(d, cap, cap_s, col_w - 16), FUCHSIA)
    return im


def speaker_slots(tier: str) -> list[tuple[dict, str]]:
    program = yaml.safe_load(open(DATA / "program.yaml"))
    members = {m["name"]: m for m in yaml.safe_load(open(DATA / "speakers.yaml"))[tier]["members"]}
    out = []
    for i, day in enumerate(program["days"], start=1):
        for s in day["sessions"]:
            for name in s.get("speakers") or []:
                if name in members:
                    start = s["time"].split(" – ")[0].split("–")[0].strip()
                    if not start.endswith(("AM", "PM")):
                        start += " " + s["time"].split()[-1]
                    out.append((members[name], f"Day {i} · {start}"))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    org = yaml.safe_load(open(DATA / "organizers.yaml"))
    # Short affiliations read better on slides.
    short = {
        "Massachusetts General Hospital · Harvard Medical School · Broad Institute": "MGH · HMS · Broad",
        "Brigham & Women's Hospital · Harvard Medical School": "BWH · HMS",
        "Dana-Farber Cancer Institute · Harvard Medical School": "DFCI · HMS",
        "Dana-Farber Cancer Institute": "DFCI",
        "Harvard T.H. Chan School of Public Health": "Harvard Chan",
        "Worcester Polytechnic Institute": "WPI",
        "Microsoft Research New England": "Microsoft Research",
        "Harvard Medical School": "HMS",
    }
    group = lambda key: [({**m, "short_affiliation": short.get(m.get("affiliation", ""), m.get("affiliation", ""))}, "")
                         for m in org[key]["members"]]
    slides = [
        ("1-co-chairs", "Conference co-chairs", group("cochairs")),
        ("2-steering-committee", "Steering committee", group("steering")),
        ("3-organizing-committee", "Organizing committee", group("organizing")),
        ("4-keynote-speakers", "Keynote speakers", speaker_slots("keynotes")),
        ("5-invited-speakers", "Invited speakers", speaker_slots("invited")),
    ]
    for fname, heading, people in slides:
        slide(heading, people).save(OUT / f"{fname}.png")
        missing = [m["name"] for m, _ in people if not photo_for(m)]
        print(f"wrote docs/slides/{fname}.png" + (f"  (initials for: {', '.join(missing)})" if missing else ""))


if __name__ == "__main__":
    main()
