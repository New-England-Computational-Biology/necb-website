# Setup guide — Google Forms + Sheets review workflow

Primary infrastructure for the NECB 2026 abstract review. Target: ~60 min, one operator, no code deploy. When you're done, the 16 reviewers have a link to their personal queue and a link to score.

Live artifacts:
- **Drive folder:** https://drive.google.com/drive/u/0/folders/1gI6bSQ3C59VxHLFXIBnxPr0HH-v2CnBR
- **Master Sheet:** https://docs.google.com/spreadsheets/d/1WSe1ONckffM-SBeBWpoZN-FORCF2LC1ZHB9ljG_dLSY/edit
- **Review Form (edit):** https://docs.google.com/forms/d/17rcU50jlrDbl8xGAdPvYYWJTDL3lbFrda3OPvhCVoXc/edit
- **Review Form (public responder link):** https://forms.gle/pPmsrcyYVuyBfGWR8
- **Reviewer filter-view URLs:** _(to add — one per reviewer)_

Assumptions:
- You have a Google account with edit rights to the shared Drive folder above.
- The chairs' emails are on hand for edit-sharing.
- The reviewers' emails are on hand for view/comment-sharing (or you'll use a link-only share).

---

## Fast path (~5 min)

The folder, sheet, and form already exist but are empty. To fill them:

1. Open the Master Sheet → **Extensions → Apps Script**.
2. Paste the contents of `docs/review/apps-script-setup.js` into `Code.gs`. Save.
3. Grant permissions on first run (Sheets + Forms + Drive scopes).
4. From the function picker, run **`setupSheets`** — builds the four tabs (`Submissions`, `Assignments`, `Scores`, `Aggregate`) with headers, formulas, dropdowns, conditional formatting.
5. Run **`setupForm`** — builds the 9 Form fields matching the rubric and links responses to the `Scores` tab.
6. In the Sheet, create per-reviewer filter views (Step 4 below) — 15 min.
7. In the Form, grab the responder link (Send → Link icon) and paste it into `kickoff-email.md`.
8. Dry-run with three dummy submissions (Step 6 below).

Everything else in this guide is the reference for what those scripts do — read on if you want to know why each formula or field is there, or if you'd rather build it by hand.

---

## Components

You'll end up with:

1. **One shared Drive folder** — `NECB 2026 · Abstract review`. Already created.
2. **One Google Sheet** inside it, with four tabs: `Submissions`, `Assignments`, `Scores`, `Aggregate`. Created empty; `setupSheets` populates.
3. **One Google Form** — the reviewer scoring form. Its responses land in the `Scores` tab automatically. `setupForm` builds it.
4. **Sixteen filter-view URLs**, one per reviewer, that scope the `Assignments` tab to just that reviewer's queue. Manual — see Step 4.

Optional:
- The bundled Apps Script also includes an `aggregateReviews` function (below) that recomputes the `Aggregate` tab in a single pass, and can be attached to an on-form-submit trigger if the formula-based aggregation misbehaves.

---

## Step 1 — Drive folder

Already created at **https://drive.google.com/drive/u/0/folders/1gI6bSQ3C59VxHLFXIBnxPr0HH-v2CnBR**. Confirm the organizing committee has **Editor** access, and that the folder isn't shared with the reviewers directly (they should only see file-level shares on specific artifacts).

## Step 2 — Master Sheet

Master Sheet is at **https://docs.google.com/spreadsheets/d/1WSe1ONckffM-SBeBWpoZN-FORCF2LC1ZHB9ljG_dLSY/edit**. Confirm it has (or add) four tabs in this order: `Submissions`, `Assignments`, `Scores`, `Aggregate`. Delete any leftover default `Sheet1`.

### Tab 1: `Submissions`

Row 1 headers (freeze row 1 via View → Freeze → 1 row):

| Column | Header | Notes |
|---|---|---|
| A | `abstract_id` | Short ID, e.g., `A001`. Chairs assign sequentially. |
| B | `title` | Paste from the ISCB export. |
| C | `authors` | Comma-separated author list. |
| D | `presenting_affiliation` | Institution of the presenting author. |
| E | `abstract_text` | 250-word text abstract. |
| F | `pdf_link` | Public link to the 1-page PDF (Drive or ISCB URL). |
| G | `topic_keywords` | 2–3 keywords chairs tag for assignment (e.g., `single-cell, ML`). |
| H | `chair_notes` | Free text; hidden from reviewers. |

**Import path.** Once ISCB delivers the submission export (CSV or Excel), paste-append into columns A–F. Fill G by hand (fastest with a keyword palette written into `chair_notes` of row 0 for reference).

### Tab 2: `Assignments`

Row 1 headers:

| Column | Header | Notes |
|---|---|---|
| A | `abstract_id` | Foreign key to `Submissions`. |
| B | `title` | `=VLOOKUP(A2, Submissions!A:F, 2, FALSE)`. Dragged down. |
| C | `topic_keywords` | `=VLOOKUP(A2, Submissions!A:G, 7, FALSE)`. |
| D | `reviewer` | Reviewer name (must match the Form dropdown exactly). |
| E | `coi_flag` | `TRUE` if there's a known conflict — chairs fill after cross-check. Rows with `TRUE` should be dropped, not scored. |
| F | `status` | Blank / `submitted` / `withdrawn` — updated by the operator or an Apps Script trigger. |
| G | `pdf_link` | `=VLOOKUP(A2, Submissions!A:F, 6, FALSE)`. Handy for reviewers. |

One row per **(abstract × reviewer)** pair. If you're doing 3 reviews per abstract, each `abstract_id` shows up in 3 rows. Chairs fill columns A + D; the rest auto-populates.

### Tab 3: `Scores`

Leave this tab empty — the Google Form will write its response header here on the first submission. After that, each row is one review.

Expected columns after the Form is linked:

`Timestamp | Reviewer | Abstract ID | Significance | Rigor | Clarity | Fit for NECB | Recommendation | Confidence | Rationale`

If you want the Python aggregation script to run on an export from this tab, rename the header row on export (or add a normalized copy in a hidden `Scores_norm` tab — see Apps Script section).

### Tab 4: `Aggregate`

Row 1 headers:

| Column | Header | Formula (row 2 downward) |
|---|---|---|
| A | `abstract_id` | `=UNIQUE(FILTER(Scores!C:C, Scores!C:C<>""))` in A2, then leave the rest blank for the spill. |
| B | `n_reviews` | `=COUNTIF(Scores!C:C, A2)` |
| C | `mean_significance` | `=IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!D:D),)` |
| D | `mean_rigor` | `=IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!E:E),)` |
| E | `mean_clarity` | `=IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!F:F),)` |
| F | `mean_fit` | `=IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!G:G),)` |
| G | `n_talk` | `=COUNTIFS(Scores!C:C, A2, Scores!H:H, "Accept as talk")` |
| H | `n_poster` | `=COUNTIFS(Scores!C:C, A2, Scores!H:H, "Accept as poster")` |
| I | `n_reject` | `=COUNTIFS(Scores!C:C, A2, Scores!H:H, "Reject")` |
| J | `mean_overall` | `=IFERROR((G2*3 + H2*2 + I2*1) / B2,)` |
| K | `mean_confidence` | `=IFERROR((COUNTIFS(Scores!C:C, A2, Scores!I:I, "Low")*1 + COUNTIFS(Scores!C:C, A2, Scores!I:I, "Med")*2 + COUNTIFS(Scores!C:C, A2, Scores!I:I, "High")*3) / B2,)` |
| L | `weighted_score` | `=J2*K2` |
| M | `disagreement_flag` | `=IF(AND(G2>0, I2>0), "talk_vs_reject", IF(STDEV.P(FILTER(Scores!H:H, Scores!C:C=A2, {3,2,1}))>1.5, "stdev>1.5", ""))` — simpler alternative: `=IF(AND(G2>0, I2>0), "talk_vs_reject", "")` |
| N | `rationales` | `=TEXTJOIN(" \| ", TRUE, FILTER(Scores!J:J, Scores!C:C=A2))` |

Freeze row 1. Sort the whole range by column L (`weighted_score`) descending for ranking. Highlight column M with conditional formatting → red on non-empty.

---

## Step 3 — Google Form

Form is at **https://docs.google.com/forms/d/17rcU50jlrDbl8xGAdPvYYWJTDL3lbFrda3OPvhCVoXc/edit**. Confirm it's named `NECB 2026 · Abstract review` and lives inside the review folder.

Form-level settings (gear icon → **Presentation** and **Responses**):
- **Collect email addresses**: off (we use the Reviewer dropdown instead — one less obstacle).
- **Restrict to N responses per person**: off — one reviewer submits many.
- **Show progress bar**: on.
- **Shuffle question order**: off.
- **Confirmation message**: `Thanks — score recorded. If you need to update a review, submit again with the same Reviewer + Abstract ID; chairs will keep the latest.`

### Questions

Copy-paste these exactly so the response column headers match the `Aggregate` formulas.

1. **Reviewer** (Dropdown, required)
   - Options (16 names, alphabetical):
     Andrew Caruso · Curie Cha · Kit Gallagher · Aditya Gorla · Lei Huang · Senbao Lu · Karna Mendonca · Zain Patel · Ben Perry · Anna Sappington · Kristen Severson · Ross Stewart · Ruohan Wang · Will White · Laura Yeoh · Nanxiang (Sam) Zhao

2. **Abstract ID** (Short answer, required)
   - Response validation → Regex → `^A\d{3}$` — matches `A001` style; adjust if you use a different scheme.

3. **Significance** (Linear scale 1–5, required)
   - Label 1: `Not significant` · Label 5: `Groundbreaking`
   - Description: paste the significance dimension from the Reviewer Packet.

4. **Rigor** (Linear scale 1–5, required)
   - Label 1: `Not sound` · Label 5: `Rigorous`

5. **Clarity** (Linear scale 1–5, required)
   - Label 1: `Poorly written` · Label 5: `Exemplary`

6. **Fit for NECB** (Linear scale 1–5, required)
   - Label 1: `Out of scope` · Label 5: `Squarely in scope`

7. **Recommendation** (Multiple choice, required)
   - `Accept as talk`
   - `Accept as poster`
   - `Reject`

8. **Confidence** (Multiple choice, required)
   - `Low`
   - `Med`
   - `High`

9. **Rationale** (Paragraph, required)
   - Description: `Two sentences — one strength, one concern.`

### Link the Form to the master Sheet

In the Form editor → **Responses** tab → click the Sheets icon → **Select existing spreadsheet** → pick `NECB 2026 · Review master` → destination sheet name: `Scores`. Confirm the Form response header lands in the `Scores` tab.

**Test it now.** Submit one dummy response. Verify:
- A row appeared in `Scores`.
- `Aggregate` picked up the abstract ID and computed row-2 values.
- The `disagreement_flag` cell is empty (as expected for one review).

## Step 4 — Per-reviewer filter views

Each reviewer needs a URL that opens the `Assignments` tab pre-filtered to their name.

For each of the 16 reviewers:

1. On the `Assignments` tab → Data → **Create a filter view** → name it `Queue — <Reviewer Name>`.
2. Filter column D (`reviewer`) → equals `<Reviewer Name>`.
3. Filter column E (`coi_flag`) → does NOT include `TRUE`.
4. Copy the URL from the address bar — it now contains `?fvid=<n>`. That's the reviewer's personal link.

Faster alternative once you have one filter view: duplicate it via the Filter views dropdown, change name + reviewer condition. Takes ~2 min/reviewer, 30 min total.

Save all 16 URLs in the folder as a plain-text note or in a hidden `chair_notes` tab — you'll paste them into the kickoff email.

## Step 5 — Share

- **Sheet**: share with reviewers as **Commenter** (they can add notes; they can't accidentally overwrite formulas). Or, if you want them to update column F (`status`) directly, **Editor** with cell-range protection on all other columns.
- **Form**: no share needed — it's public via the responder link.
- **Individual PDFs**: if you're hosting the abstract PDFs in Drive, share the folder or each PDF as **Anyone with the link — Viewer** so reviewers don't hit a permissions wall.

## Step 6 — Test end-to-end

Before Aug 15:
- Add 3 dummy submissions to `Submissions`.
- Assign each to 3 reviewers in `Assignments` (use yourself + 2 colleagues; mark COIs on one).
- Have each of the 3 people submit scores via the Form.
- Verify `Aggregate` computes correctly and disagreement is flagged when you deliberately submit conflicting recommendations.
- Delete the dummy rows before the real submissions land.

---

## Optional: Apps Script aggregation

If you'd rather not maintain the formulas manually, drop this into Extensions → Apps Script → save as `aggregate.gs`. Run manually or on Form-submit trigger.

```javascript
function aggregateReviews() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const scores = ss.getSheetByName('Scores');
  const out = ss.getSheetByName('Aggregate');

  const rows = scores.getRange(2, 1, scores.getLastRow() - 1, 10).getValues();
  // Columns (0-indexed): Timestamp, Reviewer, Abstract ID, Sig, Rigor, Clarity, Fit, Rec, Conf, Rationale
  const RECMAP = { 'Accept as talk': 3, 'Accept as poster': 2, 'Reject': 1 };
  const CONFMAP = { 'Low': 1, 'Med': 2, 'High': 3 };

  const byId = {};
  for (const r of rows) {
    const id = r[2];
    if (!id) continue;
    byId[id] = byId[id] || { sig: [], rig: [], cla: [], fit: [], rec: [], conf: [], rat: [] };
    byId[id].sig.push(r[3]);
    byId[id].rig.push(r[4]);
    byId[id].cla.push(r[5]);
    byId[id].fit.push(r[6]);
    byId[id].rec.push(RECMAP[r[7]] || 0);
    byId[id].conf.push(CONFMAP[r[8]] || 0);
    byId[id].rat.push(r[9] || '');
  }

  const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
  const stdev = a => {
    const m = mean(a);
    return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / a.length);
  };

  const result = [[
    'abstract_id', 'n_reviews',
    'mean_significance', 'mean_rigor', 'mean_clarity', 'mean_fit',
    'n_talk', 'n_poster', 'n_reject',
    'mean_overall', 'mean_confidence', 'weighted_score',
    'stdev_overall', 'disagreement_flag', 'rationales'
  ]];

  for (const id of Object.keys(byId).sort()) {
    const d = byId[id];
    const nTalk = d.rec.filter(v => v === 3).length;
    const nPoster = d.rec.filter(v => v === 2).length;
    const nReject = d.rec.filter(v => v === 1).length;
    const mOverall = mean(d.rec);
    const mConf = mean(d.conf);
    const sd = stdev(d.rec);
    let flag = '';
    if (nTalk > 0 && nReject > 0) flag = 'talk_vs_reject';
    else if (sd > 1.5) flag = 'stdev>1.5';
    result.push([
      id, d.rec.length,
      Number(mean(d.sig).toFixed(2)),
      Number(mean(d.rig).toFixed(2)),
      Number(mean(d.cla).toFixed(2)),
      Number(mean(d.fit).toFixed(2)),
      nTalk, nPoster, nReject,
      Number(mOverall.toFixed(2)),
      Number(mConf.toFixed(2)),
      Number((mOverall * mConf).toFixed(2)),
      Number(sd.toFixed(2)),
      flag,
      d.rat.filter(Boolean).join(' | ')
    ]);
  }

  out.clear();
  out.getRange(1, 1, result.length, result[0].length).setValues(result);
  out.getRange(1, 1, 1, result[0].length).setFontWeight('bold');
  out.setFrozenRows(1);

  // Sort by weighted_score desc (skip header)
  const range = out.getRange(2, 1, result.length - 1, result[0].length);
  range.sort({ column: 12, ascending: false });

  // Highlight disagreement flags
  const flagRange = out.getRange(2, 14, result.length - 1, 1);
  const rules = SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains('_')
    .setBackground('#F4C7C3')
    .setRanges([flagRange])
    .build();
  out.setConditionalFormatRules([rules]);
}
```

To run on every form submission: Apps Script → **Triggers** (clock icon) → **Add Trigger** → function `aggregateReviews` · event source `From spreadsheet` · event type `On form submit`.

---

## What still needs a human

- Assigning abstracts to reviewers (respecting COIs + institutional balance). No amount of automation replaces the chair pass on this.
- Reading through disagreement-flagged rows before author notifications go out.
- Reading the top ~5 highest-scored to confirm slot allocation.

Everything else — collection, sanity-summing, ranking, flagging — is on the Sheet.
