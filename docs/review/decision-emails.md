# Author decision emails — Fri Sep 4, 2026

Three templates for the notification wave to all 222 authors (197 regular +
25 late-breaking). The Aggregate tab (post-committee-meeting) now carries
three sub-tabs prepared by Luca:

- **Selected talks** — 22 abstracts (11/day × 2 days)
- **Accepted posters** — regular round + all late-breaking
- **Rejected posters**

Send from `newenglandcompbio@gmail.com`; per-author personalization via
`{FIRST_NAME}` and `{ABSTRACT_ID}` fields. BCC in batches of 50 or use a
mail-merge helper (see notes at the end).

---

## 1. Selected for a talk

**Subject:** NECB 2026 · Your abstract has been selected for a talk — {ABSTRACT_ID}

Dear {FIRST_NAME},

Congratulations — your abstract **{ABSTRACT_ID}** has been selected for a
**contributed talk** at NECB 2026 (Oct 1–2, 2026 · Cambridge, MA). This was a
very competitive round — 22 talks selected from ~200 submissions — so thank
you for submitting such a strong contribution.

**Format:** 10-minute presentation + 5-minute Q&A. Your slot will be
scheduled across one of the four contributed-talk sessions on Day 1 (Thu Oct 1)
or Day 2 (Fri Oct 2). We'll send the final program with your assigned slot by
**Fri Sep 18**.

**Please confirm attendance by Wed Sep 10** by replying to this email so we
can finalize the program. If for any reason you can no longer present, let us
know as soon as possible and we'll offer the slot to the next abstract on our
list.

**Register:** https://iscb.swoogo.com/necb2026/begin — **early-bird rates end
Fri Sep 11**. All presenters must be registered by regular-registration close
(Mon Sep 21).

We'll follow up separately with talk logistics (slide format, presentation
laptop, timing bell, etc.) closer to the conference.

Congratulations again — really looking forward to your talk!

Best,
NECB 2026 Organizing Committee

---

## 2. Accepted as a poster

**Subject:** NECB 2026 · Your abstract has been accepted as a poster — {ABSTRACT_ID}

Dear {FIRST_NAME},

Congratulations — your abstract **{ABSTRACT_ID}** has been accepted for
**poster presentation** at NECB 2026 (Oct 1–2, 2026 · Cambridge, MA). We had a
very strong pool of submissions this year and are excited to have your work
on display.

**Poster sessions:**

- Day 1 · Thu Oct 1 · 2:00–4:00 PM
- Day 2 · Fri Oct 2 · 2:00–4:00 PM

We'll assign your poster to one of the two sessions (per available board
space) and share your session + board number by **Fri Sep 18**.

**Poster format:** portrait, up to **48 in × 36 in (122 × 91 cm)**. Push-pins
provided. Please bring your poster with you — no on-site printing.

**Please confirm attendance by Wed Sep 10** by replying to this email so we
can plan the poster layout. Presenters must be present at their poster during
the full 2-hour session.

**Register:** https://iscb.swoogo.com/necb2026/begin — **early-bird rates end
Fri Sep 11**. All presenters must be registered by regular-registration close
(Mon Sep 21).

{ONLY_FOR_REGULAR_ROUND}
**Poster awards.** Regular-round posters are eligible for our poster-prize
competition — a small panel of judges will evaluate posters during the
sessions. Winners announced at the closing keynote on Day 2.

{ONLY_FOR_LATE_BREAKING}
Note: as a late-breaking submission, your poster is not eligible for the
poster-award competition, but is otherwise a full poster presentation.

Congratulations again — see you in October!

Best,
NECB 2026 Organizing Committee

---

## 3. Regret — not accepted

**Subject:** NECB 2026 · Update on your abstract — {ABSTRACT_ID}

Dear {FIRST_NAME},

Thank you for submitting your abstract **{ABSTRACT_ID}** to NECB 2026. We're
writing to let you know that we're unfortunately **unable to accept it** for
presentation this year.

This was a very competitive first-year cohort — we received close to 220
submissions for a symposium with 22 talk slots and limited poster capacity,
and difficult decisions had to be made. This outcome reflects the constraints
of the program size and topic balance rather than a judgment on the merit of
the work.

**You're very welcome to attend NECB 2026 as a registered attendee.** The
program spans two days of keynotes, invited talks, contributed talks, and
poster sessions covering the breadth of computational biology in New England
— we'd love to have you there.

**Register:** https://iscb.swoogo.com/necb2026/begin — early-bird rates end
Fri Sep 11.

If you have questions about the outcome or would like brief reviewer
feedback, please reply to this email.

Thank you again for supporting this inaugural symposium, and we hope to see
you at NECB 2027 with an even stronger cohort.

Best,
NECB 2026 Organizing Committee

---

## Notes for the sender

- **Split placeholder for #2** — poster acceptance has a `{ONLY_FOR_REGULAR_ROUND}`
  vs `{ONLY_FOR_LATE_BREAKING}` conditional at the end. When sending, remove
  the block that doesn't apply per author. Filter by the `round` column on the
  Submissions tab of the review master sheet.
- **Recipient list per template** — the three Aggregate sub-tabs Luca built
  are the source of truth: pull `{FIRST_NAME}`, `{ABSTRACT_ID}`, email from
  the corresponding Submissions row via VLOOKUP on `abstract_id`. Author
  emails live in the ISCB export CSVs
  (`docs/review/build/NECB-2026-Submission_2026-08-14.csv` regular round,
  `docs/review/build/NECB-2026-Submission_2026-09-01.csv` late-breaking).
- **Send mechanism** — options:
  - Gmail mail-merge extension (Yet Another Mail Merge, etc.) directly from
    the `newenglandcompbio@gmail.com` inbox: paste the template, connect to a
    sheet, hit send.
  - Apps Script that iterates the three sub-tabs and calls `GmailApp.sendEmail`
    with per-author fills; ~30 lines. Can add if we want a repeatable pipeline.
  - Manual bulk BCC by category (50/batch to avoid Gmail spam heuristics).
- **Timing** — decisions Fri Sep 4 (today); early-bird deadline Fri Sep 11.
  Sending today gives authors a full week of early-bird registration.
