#!/usr/bin/env python3
"""Allocate accepted posters to Day 1 or Day 2 for NECB 2026.

Inputs (all relative to repo root):
  - docs/review/build/submissions_paste.csv       (197 regular)
  - docs/review/build/submissions_paste_late.csv  (25 late-breaking)
  - Master poster acceptance thread's BCC list (hard-coded below; 190 emails)
  - docs/review/build/withdrawals.csv             (exclude these abstracts)
  - docs/review/build/poster_day_overrides.csv    (pin explicit day preferences)

Output:
  - docs/review/build/poster_day_assignments.csv  (abstract_id, day, ...)

Algorithm:
  1. Build accepted-poster pool = BCC list minus withdrawn minus bounced.
  2. Apply overrides — pin each specified abstract to Day 1 or Day 2.
  3. For the remaining, iterate in a fixed-seed shuffled order and assign each
     to whichever day currently has fewer abstracts sharing the primary topic
     keyword. Tie-break on total count (aim for balanced sizes), then on
     abstract_id.
  4. Late-breaking gets balanced independently of regular round so both days
     have some LB posters.

Deterministic — same input, same output.
"""
from __future__ import annotations
import csv, random, argparse, re
from collections import Counter, defaultdict
from pathlib import Path


def clean_affiliation(s: str) -> str:
    """Strip trailing zip codes, US state abbreviations, and country tokens
    from an affiliation string so the site shows just the institution.
    Idempotent — running twice is a no-op.

    State codes must be uppercase to match (avoids eating "al" from "Hospital"
    or "hi" from "Ohio"). Country tokens are case-insensitive.
    """
    if not s: return s
    s = s.strip().rstrip(".").strip()
    # Uppercase-only, word-bounded state codes so "Hospital" and "Ohio" are safe.
    US_ST = r"\b(?:A[LKZR]|C[AOT]|DE|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY]|DC)\b"

    def strip_country(s):
        return re.sub(r",?\s*(USA|U\.S\.A\.?|US|U\.S\.?|United States(?: of America)?)\s*$",
                      "", s, flags=re.I).strip().rstrip(".").rstrip(",").strip()
    def strip_zip(s):
        return re.sub(r",?\s*\d{5}(?:-\d{4})?\s*$", "", s).strip().rstrip(",").strip()
    def strip_st_zip(s):
        return re.sub(rf",?\s*{US_ST}\s+\d{{5}}(?:-\d{{4}})?\s*$", "", s).strip().rstrip(",").strip()
    def strip_city_st(s):
        # ", City, ST" at end — city is a capitalized word run
        return re.sub(rf",\s*[A-Z][A-Za-z .'’-]+,\s*{US_ST}\s*$", "", s).strip().rstrip(",").strip()
    def strip_trailing_st(s):
        return re.sub(rf",\s*{US_ST}\s*$", "", s).strip().rstrip(",").strip()

    for _ in range(4):
        prev = s
        s = strip_country(s)
        s = strip_zip(s)
        s = strip_st_zip(s)
        s = strip_city_st(s)
        s = strip_trailing_st(s)
        if s == prev: break
    # Institution-level short forms
    s = re.sub(r"\bBroad Institute of MIT and Harvard\b", "Broad Institute", s)
    return s.strip().rstrip(",").rstrip(".").strip()

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "review" / "build"
BCC_FILE = BUILD / "poster_bcc.txt"        # optional; else fallback to hard-coded
WITHDRAW = BUILD / "withdrawals.csv"
OVR = BUILD / "poster_day_overrides.csv"
OUT = BUILD / "poster_day_assignments.csv"
BOUNCED: set[str] = set()   # A008 seanrjohnson bounced originally, but Kevin
                            # reached Sean directly (sjohnson@neb.com) — he
                            # confirmed attendance, so A008 stays in the pool.

# The 190 BCC recipients from the Sep 5 poster acceptance email. Hard-coded so
# the script is self-contained. If the list changes, regenerate from the
# master thread's BCC field.
BCC_EMAILS = {e.strip().lower() for e in """
Fnu_Sujiyanto@student.uml.edu Jakob_mikhaylov@student.uml.edu Kenia.Viri@salve.edu
KulandaiSamy.Arulsamy@childrens.harvard.edu LFERREIRADASILVA@mgh.harvard.edu
Maxwell.campbell3@umassmed.edu Waverly.Carabba@tufts.edu Ziyan.Rao2@umassmed.edu
aaron.kollasch@basecamp-research.com abderrazzaq.h@northeastern.edu acandib@bu.edu
acepedadiaz@wi.mit.edu ajajoo@mclean.harvard.edu anand.ri@northeastern.edu
anastasia.leshchyk@tuftsmedicine.org andrewdr@bu.edu anthony.lau@umassmed.edu
apirani@mdanderson.org apoorva.nyu@gmail.com arda.halu@channing.harvard.edu
at3836@columbia.edu ating@wi.mit.edu avon_yang@fas.harvard.edu
baharav@broadinstitute.org bengi.yavuz@nih.gov benguebila@hsph.harvard.edu
bgl2126@columbia.edu bsanjana@bu.edu camv@bu.edu ccha2@mgh.harvard.edu
cgallagher19@mgh.harvard.edu chan.zhou@umassmed.edu chen.liao@dartmouth.edu
cheng.xiw@northeastern.edu chenyuel@mit.edu chichun_tan@brown.edu
christellemoise@gmail.com cjeffery@uic.edu ckraay@g.harvard.edu
conrad.bzura@umassmed.edu cowen@cs.tufts.edu danqiliao@windmirror.ai
dbhattacharya@vt.edu dfirer@mit.edu di.zhou@tufts.edu drew.steindl@yale.edu
eappiah@uchc.edu eimaanbilal20@gmail.com eowen@mit.edu euijin.kwon@umassmed.edu
eva.fast@pfizer.com faith.ocitti@tufts.edu gbrunette@g.harvard.edu
genevievekingsford36@gmail.com giacomo.ceoldo@childrens.harvard.edu
giasuhil@gmail.com grli4@mgh.harvard.edu hlords@bu.edu inoue019@umn.edu
iphilip7@gatech.edu isarfraz@bu.edu jeremie.darmawan@smart.mit.edu
jiang.jic@northeastern.edu jmmoy@bu.edu jocelyn.garcia@tufts.edu
juf009@ucsd.edu julia_james1@student.uml.edu k.ensafitakaldani001@umb.edu
kaifu.chen@childrens.harvard.edu karthikeyan.su@northeastern.edu
kevin.borisiak@yale.edu kristine_yang@hms.harvard.edu lesplana@wpi.edu
liaoruqi@broadinstitute.org lijiayi@broadinstitute.org lim.hyu@northeastern.edu
lina.yan2@umassmed.edu liu.zheng9@northeastern.edu liuj11@mskcc.org
lkroeh@bu.edu luc.r.francis@gmail.com lukeberg@bu.edu maa32@illinois.edu
majialan@broadinstitute.org mansooreh.ahmadian@cuanschutz.edu
mark_keller@hms.harvard.edu martelli@broadinstitute.org mary.likhite@umassmed.edu
marykafi@uconn.edu matthew.lin.earth@outlook.com mccarter.calvin@gmail.com
expy@bu.edu mendonca.k@northeastern.edu michael.tian@umassmed.edu
mingxin_liu@brown.edu mjo@neu.edu mkapoor@iastate.edu mn667421@ohio.edu
mohanty@hms.harvard.edu msrosito@ds.dfci.harvard.edu mybadendieck@wpi.edu
myousry@bu.edu nayaksp@bu.edu nezar.abdennur@umassmed.edu
nguyen_tran2@student.uml.edu nicole.shedd@umassmed.edu nishab@iiitd.ac.in
nramani@bu.edu omrajesh2023@gmail.com palmsundaygirl@gmail.com
peterren@g.harvard.edu pilu1@mgh.harvard.edu ppooyan@meei.harvard.edu
prustysp@bu.edu rawat.sam@northeastern.edu rbationo90@gmail.com
renjiewu02@gmail.com ritikarvl2627@gmail.com ruohan_wang@brown.edu
ruohongw@bu.edu ryan_seaman@hms.harvard.edu scarver@g.harvard.edu
schowdhu@bu.edu sjohnson@neb.com shastrya@bu.edu
shogan.sugumarswamy@childrens.harvard.edu shreyasgr@gmail.com
siddharth.viswanath@yale.edu skcheng@umich.edu slu3@wpi.edu smlewis@wpi.edu
sn503421@ohio.edu sng2027@bu.edu sogden@udallas.edu stelliou@mgh.harvard.edu
suhas_rao@hms.harvard.edu svinia2@uic.edu taiqi_li@hms.harvard.edu
tanggis.bohnuud@basecamp-research.com tanzila_alam@hms.harvard.edu
temi@attentionlab.ai tetsuo.momiy@utec.edu.pe tianhao_luo@g.harvard.edu
tongxin_wang@hms.harvard.edu tyler_aprati@dfci.harvard.edu ug2084@nyu.edu
uyenchu@bu.edu vedat.yilmaz@umassmed.edu victoria.r.howard@vanderbilt.edu
vyas.ja@northeastern.edu weisburd@broadinstitute.org weiwei.lou@tufts.edu
widenerm@bc.edu william_li@hms.harvard.edu wonyl@bu.edu
yikuuun.zhang@gmail.com yuncheng.duan1@umassmed.edu yunmai.wang@yale.edu
yxu5009@psu.edu zeyuan.song@tuftsmedicine.org zhi.qu0509@gmail.com
ziang@gatech.edu zinjuwadia.r@northeastern.edu ziqi_fu@g.harvard.edu
zpatel@mgh.harvard.edu chenbi12@msu.edu cnptp@missouri.edu dkorkin1@wpi.edu
dubingxue73@gmail.com elliot@elliottower.ai gani@umass.edu hppeng@tmu.edu.tw
kumarp79584@gmail.com makenna.rodriguez1@howard.edu matthew.funk1@umassmed.edu
matthew_leventhal@dfci.harvard.edu mb13@uw.edu michail_andreopoulos@g.harvard.edu
mroddur2@illinois.edu naveen.v@northeastern.edu nesma.hassan3991@gmail.com
p.enrique.soares@gmail.com pandey.vikas.prime@osaka-u.ac.jp
phahnel@broadinstitute.org ryansynk@umd.edu selvakumaran.m@northeastern.edu
seonghwan_jun@urmc.rochester.edu stapar@my.lonestar.edu zhao.xiw@northeastern.edu
you.yu@northeastern.edu
""".split()}


def load_submissions():
    """Return dict[abstract_id] = {email, name, affiliation, title, keywords, round}."""
    subs = {}
    for path, round_ in [
        (BUILD/"submissions_paste.csv", "regular"),
        (BUILD/"submissions_paste_late.csv", "late-breaking"),
    ]:
        with open(path) as f:
            for row in csv.reader(f):
                if len(row) < 8 or not row[0].startswith("A"):
                    continue
                subs[row[0]] = {
                    "email": None,   # filled below via ISCB CSVs
                    "title": row[1].strip(),
                    "authors": row[2],
                    "affiliation": row[3].strip(),
                    "keywords": [kw.strip() for kw in row[6].split(";") if kw.strip()],
                    "round": round_,
                }
    # Map email → abstract_id via ISCB CSVs (using title match)
    title_to_aid = {v["title"][:60]: aid for aid, v in subs.items() if v["title"]}
    for path in [ROOT/"NECB-2026-Submission_2026-08-15.csv",
                 ROOT/"NECB-2026-Submission_2026-09-01.csv"]:
        with open(path) as f:
            for row in csv.DictReader(f):
                email = (row.get("Email","") or "").strip().lower()
                title = (row.get("Title","") or "").strip()
                if not email or not title: continue
                for prefix, aid in title_to_aid.items():
                    if prefix and (prefix in title or title[:60] in prefix):
                        subs[aid]["email"] = email
                        subs[aid]["name"] = row.get("Name","").strip()
                        break

    # Manual overrides for BCC-email → abstract_id where the ISCB record has
    # bad data (title = job title, malformed email, etc.). These pin the
    # submitter to a specific abstract they represent.
    MANUAL_EMAIL_TO_AID = {
        # (email, abstract_id, presenter_name-fallback if ISCB match missed it)
        "temi@attentionlab.ai":                    ("A002", "Noah Abasciano"),   # Temitope was the submitter; Noah is first author
        "you.yu@northeastern.edu":                 ("A208", "Yukai You"),
        "gani@umass.edu":                          ("A219", "Godwin Ani"),
        "giacomo.ceoldo@childrens.harvard.edu":    ("A077", "Giacomo Ceoldo"),   # ISCB Title was 'PhD'; corrected working title in-place
        "makenna.rodriguez1@howard.edu":           ("A204", "Makenna Rodriguez"),  # ISCB record had .com typo
    }
    # Force these — the ISCB row's email may already be set but wrong (typo)
    for email, (aid, fallback_name) in MANUAL_EMAIL_TO_AID.items():
        if aid in subs:
            subs[aid]["email"] = email
            if not subs[aid].get("name"):
                subs[aid]["name"] = fallback_name

    # Presenter-name corrections where ISCB's registration entry was
    # miscapitalized. Applied unconditionally after email fixes above.
    MANUAL_NAME_FIX = {
        "A094": "Edwin Moses Appiah",
    }
    for aid, name in MANUAL_NAME_FIX.items():
        if aid in subs:
            subs[aid]["name"] = name

    # Affiliation updates the presenter has asked us to reflect (job moves,
    # renamed labs, corrections). Overrides the presenting_affiliation from
    # the submissions CSV.
    MANUAL_AFFILIATION_FIX = {
        "A050": "Aureka Biotechnologies",  # Calvin McCarter — moved from BigHat Biosciences (2026-09-15)
    }
    for aid, aff in MANUAL_AFFILIATION_FIX.items():
        if aid in subs:
            subs[aid]["affiliation"] = aff
    return subs


def load_withdrawals():
    ids = set()
    if not WITHDRAW.exists(): return ids
    with open(WITHDRAW) as f:
        for row in csv.DictReader(f):
            if row.get("type") == "poster" or row.get("type","").startswith("poster"):
                ids.add(row["abstract_id"])
    return ids


def load_overrides():
    """Return dict[abstract_id] = day (1 or 2)."""
    out = {}
    if not OVR.exists(): return out
    with open(OVR) as f:
        for row in csv.DictReader(f):
            aid = row.get("abstract_id","").strip()
            day = row.get("day","").strip()
            if aid and day in ("1","2"):
                out[aid] = int(day)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261001,
                        help="Random seed for the greedy shuffle (default: 20261001)")
    parser.add_argument("--include-no-reply", action="store_true", default=True,
                        help="Include non-responders in the allocation (default: yes; they're still officially accepted)")
    args = parser.parse_args()

    subs = load_submissions()
    withdrawn = load_withdrawals()
    overrides = load_overrides()
    print(f"loaded {len(subs)} submissions, {len(withdrawn)} withdrawals, {len(overrides)} overrides")

    # Build accepted-poster pool: BCC → abstract_id, minus withdrawals + bounces
    email_to_aid = {v["email"]: aid for aid, v in subs.items() if v.get("email")}
    accepted = []
    unresolved = []
    for email in sorted(BCC_EMAILS):
        if email in BOUNCED:
            continue
        aid = email_to_aid.get(email)
        if not aid:
            unresolved.append(email)
            continue
        if aid in withdrawn:
            continue
        accepted.append(aid)
    print(f"accepted pool: {len(accepted)}  (bounced={len(BCC_EMAILS & BOUNCED)}, "
          f"unresolved={len(unresolved)}, dropped-withdrawn={len(withdrawn)})")
    if unresolved:
        print(f"  unresolved-email BCC entries: {unresolved}")

    # Apply overrides first
    day_of = {}
    for aid, day in overrides.items():
        if aid in accepted:
            day_of[aid] = day

    # Greedy topic-balanced allocation for the rest
    rng = random.Random(args.seed)
    remaining = [aid for aid in accepted if aid not in day_of]
    rng.shuffle(remaining)

    # Separate regular vs late-breaking so each is balanced independently
    late = [aid for aid in remaining if subs[aid]["round"] == "late-breaking"]
    reg  = [aid for aid in remaining if subs[aid]["round"] == "regular"]

    def pick_day(aid, day_of, kw_by_day, count_by_day):
        kws = set(subs[aid]["keywords"][:3])  # top-3 keywords
        # score: how many existing posters on each day share ANY of aid's top-3 kws
        overlap = {1: sum(kw_by_day[1][k] for k in kws),
                   2: sum(kw_by_day[2][k] for k in kws)}
        # Prefer day with lower overlap; tie-break by lower total count
        return min([1,2], key=lambda d: (overlap[d], count_by_day[d]))

    kw_by_day = {1: Counter(), 2: Counter()}
    count_by_day = {1: 0, 2: 0}
    # Seed from overrides
    for aid, d in day_of.items():
        kw_by_day[d].update(subs[aid]["keywords"][:3])
        count_by_day[d] += 1

    for aid in reg + late:
        d = pick_day(aid, day_of, kw_by_day, count_by_day)
        day_of[aid] = d
        kw_by_day[d].update(subs[aid]["keywords"][:3])
        count_by_day[d] += 1

    # Write output
    fields = ["abstract_id","day","presenter","email","affiliation","round","title","keywords","reason"]
    with open(OUT, "w") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        # Sort by day then abstract_id
        for aid in sorted(day_of, key=lambda a: (day_of[a], a)):
            s = subs[aid]
            reason = "override" if aid in overrides else "auto"
            w.writerow({
                "abstract_id": aid, "day": day_of[aid],
                "presenter": s.get("name",""), "email": s.get("email",""),
                "affiliation": s.get("affiliation",""), "round": s["round"],
                "title": s["title"][:120], "keywords": "; ".join(s["keywords"][:5]),
                "reason": reason,
            })
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  Day 1: {count_by_day[1]}  (regular={sum(1 for a in day_of if day_of[a]==1 and subs[a]['round']=='regular')}, "
          f"late={sum(1 for a in day_of if day_of[a]==1 and subs[a]['round']=='late-breaking')})")
    print(f"  Day 2: {count_by_day[2]}  (regular={sum(1 for a in day_of if day_of[a]==2 and subs[a]['round']=='regular')}, "
          f"late={sum(1 for a in day_of if day_of[a]==2 and subs[a]['round']=='late-breaking')})")

    # --- Also emit data/posterSessions.yaml so Hugo can render the on-site
    # poster-sessions list. Only the fields the site needs go in here; email
    # stays out. Ordered by abstract_id within each day.
    yaml_path = ROOT / "data" / "posterSessions.yaml"
    def esc(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    day_meta = [
        (1, "Day 1 · Thu Oct 1, 2026", "2:15–4:15 PM"),
        (2, "Day 2 · Fri Oct 2, 2026", "2:15–4:15 PM"),
    ]
    lines = [
        'note: "Poster sessions run 2:15–4:15 PM on both days. Full abstract text and board numbers will be published in the program book (PDF) closer to the meeting."',
        "days:",
    ]
    for day_num, label, time in day_meta:
        aids = sorted([a for a, d in day_of.items() if d == day_num])
        lines.append(f'  - label: {esc(label)}')
        lines.append(f'    time: {esc(time)}')
        lines.append(f'    count: {len(aids)}')
        lines.append(f'    posters:')
        for aid in aids:
            s = subs[aid]
            lines.append(f'      - abstract_id: {esc(aid)}')
            lines.append(f'        title: {esc(s["title"].rstrip(" .").strip())}')
            lines.append(f'        presenter: {esc(s.get("name",""))}')
            lines.append(f'        affiliation: {esc(clean_affiliation(s["affiliation"]))}')
            lines.append(f'        round: {esc(s["round"])}')
    yaml_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {yaml_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
