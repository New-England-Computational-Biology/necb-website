/**
 * NECB 2026 · Abstract Review — one-shot setup.
 *
 * How to use:
 *   1. Open the master Sheet:
 *      https://docs.google.com/spreadsheets/d/1WSe1ONckffM-SBeBWpoZN-FORCF2LC1ZHB9ljG_dLSY/edit
 *   2. Extensions → Apps Script. Paste this file's contents in.
 *   3. Save. Run the two setup functions from the toolbar function picker:
 *        a. `setupSheets`  — builds the four sheet tabs.
 *        b. `setupForm`    — builds the 9 Form fields and links responses to `Scores`.
 *      (Grant permissions the first time — you'll be asked for Sheets, Forms, and Drive scopes.)
 *   4. Refresh the Sheet + reload the Form editor. Both are ready.
 *
 * Safe to re-run:
 *   - `setupSheets` clears each tab first, then rebuilds. Existing data on
 *     `Scores` is preserved (see LEAVE_SCORES_ALONE) because it's the Form
 *     destination.
 *   - `setupForm` clears any existing items on the Form before adding fresh ones.
 *     Any responses already collected are unaffected (they live in the Sheet).
 */

const FORM_ID = '17rcU50jlrDbl8xGAdPvYYWJTDL3lbFrda3OPvhCVoXc';
const SHEET_ID = '1WSe1ONckffM-SBeBWpoZN-FORCF2LC1ZHB9ljG_dLSY';
const REVIEWERS = [
  'Ritwik Anand', 'Andrew Caruso', 'Curie Cha', 'Xiwei Cheng', 'Kishalay Das',
  'Kit Gallagher', 'Jocelyn Garcia', 'Aditya Gorla', 'Lei Huang',
  'Benjamin Jones', 'Panos Ketonis', 'Anurendra Kumar', 'Senbao Lu',
  'Karna Mendonca', 'Zain Patel', 'Ben Perry', 'Anna Sappington',
  'Kristen Severson', 'Ross Stewart', 'Siddharth Viswanath', 'Ruohan Wang',
  'Will White', 'Ke Xu', 'Laura Yeoh', 'Yikun Zhang', 'Nanxiang (Sam) Zhao'
];

const LEAVE_SCORES_ALONE = true;

function setupSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  setupSubmissions_(ss);
  setupAssignments_(ss);
  if (!LEAVE_SCORES_ALONE) setupScoresHeader_(ss);
  setupAggregate_(ss);
  removeDefaultSheet_(ss);
  SpreadsheetApp.getUi().alert('NECB review sheet: four tabs ready.');
}

/* Recovery entry points — invoke these individually from the function picker
 * to rebuild just one tab without touching the others.
 * Use `rebuildAggregate` if the Aggregate tab lost references to Scores after
 * a setupForm re-run (Scores tab gets recreated and formula refs go stale).
 */
function rebuildAggregate() {
  setupAggregate_(SpreadsheetApp.openById(SHEET_ID));
  // getUi() only works when invoked from a bound sheet context; wrap so the
  // rebuild is never blocked by a UI toast that can't be shown.
  try { SpreadsheetApp.getUi().alert('Aggregate tab rebuilt.'); } catch (e) { Logger.log('Aggregate tab rebuilt.'); }
}

function rebuildScoresHeader() {
  setupScoresHeader_(SpreadsheetApp.openById(SHEET_ID));
  SpreadsheetApp.getUi().alert('Scores header rebuilt.');
}

/* ---------- Submissions ---------- */
function setupSubmissions_(ss) {
  const sh = getOrCreate_(ss, 'Submissions');
  sh.clear();

  const headers = [
    'abstract_id', 'title', 'authors', 'presenting_affiliation',
    'abstract_text', 'pdf_link', 'topic_keywords', 'round', 'chair_notes'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);

  styleHeader_(sh, headers.length);
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, 1, 90);   // abstract_id
  sh.setColumnWidths(2, 1, 320);  // title
  sh.setColumnWidths(3, 1, 260);  // authors
  sh.setColumnWidths(4, 1, 220);  // presenting_affiliation
  sh.setColumnWidths(5, 1, 420);  // abstract_text
  sh.setColumnWidths(6, 1, 260);  // pdf_link
  sh.setColumnWidths(7, 1, 220);  // topic_keywords
  sh.setColumnWidths(8, 1, 120);  // round (regular / late-breaking)
  sh.setColumnWidths(9, 1, 240);  // chair_notes

  // Wrap text in the abstract column
  sh.getRange(2, 5, sh.getMaxRows() - 1, 1)
    .setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
}

/* ---------- Assignments ---------- */
function setupAssignments_(ss) {
  const sh = getOrCreate_(ss, 'Assignments');
  sh.clear();

  const headers = [
    'abstract_id', 'title', 'topic_keywords', 'reviewer',
    'coi_flag', 'status', 'pdf_link', 'topic_affinity', 'abstract_text',
    'authors', 'presenting_affiliation'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  styleHeader_(sh, headers.length);
  sh.setFrozenRows(1);

  sh.setColumnWidths(1, 1, 90);
  sh.setColumnWidths(2, 1, 320);
  sh.setColumnWidths(3, 1, 220);
  sh.setColumnWidths(4, 1, 200);
  sh.setColumnWidths(5, 1, 80);
  sh.setColumnWidths(6, 1, 110);
  sh.setColumnWidths(7, 1, 260);
  sh.setColumnWidths(8, 1, 110);   // topic_affinity
  sh.setColumnWidths(9, 1, 500);   // abstract_text (wide)
  sh.setColumnWidths(10, 1, 340);  // authors (medium)
  sh.setColumnWidths(11, 1, 240);  // presenting_affiliation

  // Fill formulas for rows 2..N (bump if you expect more assignments).
  // All VLOOKUP formulas self-reference via INDIRECT("A"&ROW()) so they
  // survive paste-shift when reviewers or ops paste new rows.
  const N = 1000;
  const titleFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 2, FALSE),)';
  const topicsFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 7, FALSE),)';
  const pdfFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 6, FALSE),)';
  const abstractFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 5, FALSE),)';
  const authorsFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 3, FALSE),)';
  const affilFormula = '=IFERROR(VLOOKUP(INDIRECT("A"&ROW()), Submissions!A:I, 4, FALSE),)';

  const fill = (col, formula) => {
    const rng = sh.getRange(2, col, N, 1);
    rng.setFormulas(Array.from({ length: N }, () => [formula]));
  };
  fill(2, titleFormula);      // title
  fill(3, topicsFormula);     // topic_keywords
  fill(7, pdfFormula);        // pdf_link
  fill(9, abstractFormula);   // abstract_text (col I)
  fill(10, authorsFormula);   // authors (col J)
  fill(11, affilFormula);     // presenting_affiliation (col K)

  // Wrap the wide columns so reviewers can read them inline.
  sh.getRange(2, 9, N, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);   // abstract_text
  sh.getRange(2, 10, N, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);  // authors
  sh.getRange(2, 11, N, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);  // presenting_affiliation

  // Reviewer dropdown — validated against the 16-name list
  const revRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(REVIEWERS, true)
    .setAllowInvalid(false)
    .build();
  sh.getRange(2, 4, N, 1).setDataValidation(revRule);

  // coi_flag as TRUE / FALSE checkbox
  const coiRng = sh.getRange(2, 5, N, 1);
  coiRng.insertCheckboxes();

  // status dropdown
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['', 'submitted', 'withdrawn', 'reassigned'], true)
    .setAllowInvalid(false)
    .build();
  sh.getRange(2, 6, N, 1).setDataValidation(statusRule);

  // Grey-out rows where coi_flag is TRUE
  const coiFormat = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$E2=TRUE')
    .setBackground('#EEEEEE')
    .setFontColor('#888888')
    .setRanges([sh.getRange(2, 1, N, 11)])
    .build();
  sh.setConditionalFormatRules([coiFormat]);
}

/* ---------- Scores (only the header) ---------- */
function setupScoresHeader_(ss) {
  const sh = getOrCreate_(ss, 'Scores');
  sh.clear();
  const headers = [
    'Timestamp', 'Reviewer', 'Abstract ID',
    'Significance', 'Rigor', 'Clarity', 'Fit for NECB',
    'Recommendation', 'Confidence', 'Rationale'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  styleHeader_(sh, headers.length);
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, 1, 160);
  sh.setColumnWidths(2, 1, 200);
  sh.setColumnWidths(3, 1, 110);
  sh.setColumnWidths(4, 4, 90);
  sh.setColumnWidths(8, 1, 180);
  sh.setColumnWidths(9, 1, 110);
  sh.setColumnWidths(10, 1, 460);
  sh.getRange(2, 10, sh.getMaxRows() - 1, 1)
    .setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
}

/* ---------- Aggregate ---------- */
function setupAggregate_(ss) {
  const sh = getOrCreate_(ss, 'Aggregate');
  sh.clear();

  const headers = [
    'abstract_id', 'title', 'authors', 'presenting_affiliation', 'n_reviews',
    'mean_significance', 'mean_rigor', 'mean_clarity', 'mean_fit',
    'n_talk', 'n_poster', 'n_reject', 'recommendation',
    'mean_overall', 'mean_confidence', 'weighted_score',
    'disagreement_flag', 'rationales'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  styleHeader_(sh, headers.length);
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, 1, 100);   // abstract_id
  sh.setColumnWidths(2, 1, 320);   // title
  sh.setColumnWidths(3, 1, 260);   // authors
  sh.setColumnWidths(4, 1, 220);   // presenting_affiliation
  sh.setColumnWidths(5, 1, 80);    // n_reviews
  sh.setColumnWidths(6, 4, 110);   // mean_significance..mean_fit
  sh.setColumnWidths(10, 3, 70);   // n_talk / n_poster / n_reject
  sh.setColumnWidths(13, 1, 120);  // recommendation
  sh.setColumnWidths(14, 3, 130);  // mean_overall / mean_confidence / weighted_score
  sh.setColumnWidths(17, 1, 160);  // disagreement_flag
  sh.setColumnWidths(18, 1, 500);  // rationales

  // A2 spills the unique abstract IDs from Scores; B-R compute per-abstract
  sh.getRange('A2').setFormula(
    `=IFERROR(SORT(UNIQUE(FILTER(Scores!C2:C, Scores!C2:C<>""))),)`
  );

  // Row-2 formulas that spread down as new abstracts show up.
  // {R} is a placeholder for the row number — we substitute it below so we
  // don't accidentally hit constants like the *2 poster/Med weight.
  const perRow = [
    // B: title (from Submissions)
    `=IFERROR(VLOOKUP(A{R}, Submissions!$A:$I, 2, FALSE),)`,
    // C: authors (from Submissions)
    `=IFERROR(VLOOKUP(A{R}, Submissions!$A:$I, 3, FALSE),)`,
    // D: presenting_affiliation (from Submissions)
    `=IFERROR(VLOOKUP(A{R}, Submissions!$A:$I, 4, FALSE),)`,
    // E: n_reviews
    `=IF(A{R}="","",COUNTIF(Scores!C:C, A{R}))`,
    // F: mean_significance
    `=IF(A{R}="","",IFERROR(AVERAGEIF(Scores!C:C, A{R}, Scores!D:D),))`,
    // G: mean_rigor
    `=IF(A{R}="","",IFERROR(AVERAGEIF(Scores!C:C, A{R}, Scores!E:E),))`,
    // H: mean_clarity
    `=IF(A{R}="","",IFERROR(AVERAGEIF(Scores!C:C, A{R}, Scores!F:F),))`,
    // I: mean_fit
    `=IF(A{R}="","",IFERROR(AVERAGEIF(Scores!C:C, A{R}, Scores!G:G),))`,
    // J: n_talk
    `=IF(A{R}="","",COUNTIFS(Scores!C:C, A{R}, Scores!H:H, "Accept as talk"))`,
    // K: n_poster
    `=IF(A{R}="","",COUNTIFS(Scores!C:C, A{R}, Scores!H:H, "Accept as poster"))`,
    // L: n_reject
    `=IF(A{R}="","",COUNTIFS(Scores!C:C, A{R}, Scores!H:H, "Reject"))`,
    // M: recommendation (plurality of reviewer votes; ties → higher category talk>poster>reject)
    `=IF(OR(A{R}="",E{R}=0),,IFS(J{R}>=MAX(K{R},L{R}),"talk",K{R}>=L{R},"poster",TRUE,"reject"))`,
    // N: mean_overall  (weights: talk=3, poster=2, reject=1)
    `=IF(OR(A{R}="",E{R}=0),,IFERROR((J{R}*3+K{R}*2+L{R}*1)/E{R},))`,
    // O: mean_confidence  (weights: Low=1, Med=2, High=3)
    `=IF(OR(A{R}="",E{R}=0),,IFERROR((COUNTIFS(Scores!C:C,A{R},Scores!I:I,"Low")*1+COUNTIFS(Scores!C:C,A{R},Scores!I:I,"Med")*2+COUNTIFS(Scores!C:C,A{R},Scores!I:I,"High")*3)/E{R},))`,
    // P: weighted_score
    `=IF(OR(N{R}="",O{R}=""),,N{R}*O{R})`,
    // Q: disagreement_flag
    `=IF(A{R}="","",IF(AND(J{R}>0,L{R}>0),"talk_vs_reject",""))`,
    // R: rationales
    `=IF(A{R}="","",TEXTJOIN(" | ", TRUE, FILTER(Scores!J:J, Scores!C:C=A{R})))`
  ];

  // Sized for our current abstract ID space (197 regular + 25 late-breaking
  // = 222, with headroom). Keep small — every extra row multiplies the
  // per-column FILTER/VLOOKUP recalc cost against Scores and Submissions.
  const N = 250;

  // Build a single N × perRow.length grid and write all formulas in ONE
  // setFormulas call. Writing column-by-column used to trigger an
  // intermediate recalc after every column and made rebuildAggregate
  // effectively hang; batching keeps the whole rebuild under ~15 s.
  const grid = [];
  for (let r = 0; r < N; r++) {
    const rowNum = String(r + 2);
    grid.push(perRow.map(f => f.replace(/\{R\}/g, rowNum)));
  }
  sh.getRange(2, 2, N, perRow.length).setFormulas(grid);

  // Format numeric columns to 2 decimals (F-I means; N-P mean_overall/mean_conf/weighted)
  sh.getRange(2, 6, N, 4).setNumberFormat('0.00');
  sh.getRange(2, 14, N, 3).setNumberFormat('0.00');

  // Wrap title / authors / affiliation / rationales so long text is readable
  sh.getRange(2, 2, N, 3).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  sh.getRange(2, 18, N, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);

  // Highlight disagreements (col Q)
  const flagFormat = SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains('_')
    .setBackground('#F4C7C3')
    .setFontColor('#8B0000')
    .setRanges([sh.getRange(2, 17, N, 1)])
    .build();
  sh.setConditionalFormatRules([flagFormat]);
}

/* ---------- Helpers ---------- */
function getOrCreate_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function styleHeader_(sh, nCols) {
  sh.getRange(1, 1, 1, nCols)
    .setFontWeight('bold')
    .setBackground('#1C3D7B')
    .setFontColor('#FFFFFF')
    .setHorizontalAlignment('left');
  sh.getRange(1, 1, 1, nCols).setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);
}

function removeDefaultSheet_(ss) {
  const def = ss.getSheetByName('Sheet1');
  if (def && ss.getSheets().length > 1) ss.deleteSheet(def);
}

/* =========================================================
 * FORM SETUP
 * Builds all 9 questions on the review Form and links the
 * responses to the `Scores` tab on the master Sheet.
 * ========================================================= */

function setupForm() {
  const form = FormApp.openById(FORM_ID);

  // Reset — remove all existing items so re-runs land on a clean form.
  form.getItems().forEach(item => form.deleteItem(item));

  form.setTitle('NECB 2026 · Abstract review');
  form.setDescription(
    'Thanks for helping select NECB 2026 abstracts. For each submission assigned to you: ' +
    'score the four rubric dimensions (1–5), pick an overall recommendation, note your ' +
    'confidence, and add a two-sentence rationale — one strength, one concern. ' +
    'Rubric in your kickoff email packet. Reviews close Thu Sep 3 · 11:59 PM ET.'
  );
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setLimitOneResponsePerUser(false);
  form.setShowLinkToRespondAgain(true);
  form.setProgressBar(true);
  form.setConfirmationMessage(
    'Thanks — score recorded. If you need to update a review, submit again with the ' +
    'same Reviewer + Abstract ID; chairs will keep the latest.'
  );

  // 1. Reviewer
  form.addListItem()
    .setTitle('Reviewer')
    .setRequired(true)
    .setChoiceValues(REVIEWERS);

  // 2. Abstract ID
  const abstractIdValidation = FormApp.createTextValidation()
    .setHelpText('Format: A followed by three digits (e.g. A001).')
    .requireTextMatchesPattern('^A\\d{3}$')
    .build();
  form.addTextItem()
    .setTitle('Abstract ID')
    .setHelpText('Copy from the abstract_id column in your assignments queue.')
    .setRequired(true)
    .setValidation(abstractIdValidation);

  // 3–6. Four 1–5 scales
  addScale_(form, 'Significance',
    'Is the question important? Would the result advance the field?',
    'Not significant', 'Groundbreaking');

  addScale_(form, 'Rigor',
    'Is the approach sound? Are the claims supported by the analysis?',
    'Not sound', 'Rigorous');

  addScale_(form, 'Clarity',
    'Is the abstract well-written and legible without prior context?',
    'Poorly written', 'Exemplary');

  addScale_(form, 'Fit for NECB',
    'Is this computational biology and appropriate for a regional New England symposium?',
    'Out of scope', 'Squarely in scope');

  // 7. Recommendation
  form.addMultipleChoiceItem()
    .setTitle('Recommendation')
    .setHelpText('Carries more weight than the individual dimension scores — use it decisively.')
    .setRequired(true)
    .setChoiceValues(['Accept as talk', 'Accept as poster', 'Reject']);

  // 8. Confidence
  form.addMultipleChoiceItem()
    .setTitle('Confidence')
    .setHelpText('How familiar are you with this topic?')
    .setRequired(true)
    .setChoiceValues(['Low', 'Med', 'High']);

  // 9. Rationale
  form.addParagraphTextItem()
    .setTitle('Rationale')
    .setHelpText('Two sentences — one strength, one concern.')
    .setRequired(true);

  // Link responses → master spreadsheet.
  // FormApp lands responses in an auto-created tab; we rename it to `Scores`.
  form.setDestination(FormApp.DestinationType.SPREADSHEET, SHEET_ID);

  SpreadsheetApp.flush();
  Utilities.sleep(600); // give Sheets a moment to create the destination tab

  const ss = SpreadsheetApp.openById(SHEET_ID);
  renameResponseSheetToScores_(ss);

  Logger.log('Form setup complete. Responder link: ' + form.getPublishedUrl());
}

function addScale_(form, title, helpText, low, high) {
  form.addScaleItem()
    .setTitle(title)
    .setHelpText(helpText)
    .setBounds(1, 5)
    .setLabels(low, high)
    .setRequired(true);
}

/* =========================================================
 * FILTER-VIEW GENERATOR
 * Creates one filter view per reviewer on the Assignments tab.
 * Each filter shows only that reviewer's queue with coi_flag != TRUE.
 *
 * PREREQUISITE — enable Sheets Advanced Service (one-time):
 *   Apps Script editor → Services (left sidebar, "+" icon) →
 *   Google Sheets API → Add.
 *
 * Safe to re-run: any existing filter view whose title begins with
 * "Queue — " is deleted first, then rebuilt.
 * ========================================================= */

function generateFilterViews() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const assignments = ss.getSheetByName('Assignments');
  if (!assignments) {
    SpreadsheetApp.getUi().alert('No Assignments tab. Run setupSheets first.');
    return;
  }

  // Look up sheet ID + existing filter views
  const meta = Sheets.Spreadsheets.get(SHEET_ID, {
    fields: 'sheets(properties(sheetId,title),filterViews(filterViewId,title))',
  });
  const sheetMeta = meta.sheets.find(s => s.properties.title === 'Assignments');
  const sheetId = sheetMeta.properties.sheetId;

  // Delete previous per-reviewer filter views so re-runs land cleanly
  const oldFilters = sheetMeta.filterViews || [];
  const deleteRequests = oldFilters
    .filter(fv => fv.title && fv.title.startsWith('Queue — '))
    .map(fv => ({ deleteFilterView: { filterId: fv.filterViewId } }));
  if (deleteRequests.length) {
    Sheets.Spreadsheets.batchUpdate({ requests: deleteRequests }, SHEET_ID);
  }

  // One addFilterView request per reviewer
  const addRequests = REVIEWERS.map(reviewer => ({
    addFilterView: {
      filter: {
        title: `Queue — ${reviewer}`,
        range: {
          sheetId: sheetId,
          startRowIndex: 0,
          endRowIndex: 1001,
          startColumnIndex: 0,
          endColumnIndex: 11,
        },
        criteria: {
          '3': {  // reviewer column D (0-indexed 3)
            condition: {
              type: 'TEXT_EQ',
              values: [{ userEnteredValue: reviewer }],
            },
          },
          '4': {  // coi_flag column E (0-indexed 4) — hide any row marked TRUE
            hiddenValues: ['TRUE'],
          },
        },
      },
    },
  }));

  const resp = Sheets.Spreadsheets.batchUpdate({ requests: addRequests }, SHEET_ID);
  const replies = resp.replies || [];

  // Collect URLs
  const urls = [];
  for (let i = 0; i < REVIEWERS.length; i++) {
    const fvid = replies[i].addFilterView.filter.filterViewId;
    const url = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit?gid=${sheetId}&fvid=${fvid}`;
    urls.push([REVIEWERS[i], url]);
    Logger.log(`${REVIEWERS[i]}\t${url}`);
  }

  // Persist to a "Reviewer URLs" tab for copy-paste into the kickoff email
  let urlSheet = ss.getSheetByName('Reviewer URLs');
  if (urlSheet) urlSheet.clear();
  else urlSheet = ss.insertSheet('Reviewer URLs');
  urlSheet.getRange(1, 1, 1, 2).setValues([['reviewer', 'filter_view_url']]);
  urlSheet.getRange(2, 1, urls.length, 2).setValues(urls);
  urlSheet.getRange(1, 1, 1, 2)
    .setFontWeight('bold').setBackground('#1C3D7B').setFontColor('#FFFFFF');
  urlSheet.setFrozenRows(1);
  urlSheet.setColumnWidths(1, 1, 200);
  urlSheet.setColumnWidths(2, 1, 600);

  SpreadsheetApp.getUi().alert(
    `Generated ${REVIEWERS.length} filter views.\n\n` +
    `URLs are on the "Reviewer URLs" tab — copy into the kickoff email.`
  );
}

function renameResponseSheetToScores_(ss) {
  // The Form auto-creates a sheet named 'Form Responses N' — find the newest one.
  const existingScores = ss.getSheetByName('Scores');

  const candidates = ss.getSheets().filter(s => /^Form Responses/i.test(s.getName()));
  if (candidates.length === 0) {
    Logger.log('No Form Responses sheet found to rename. Rename manually to "Scores".');
    return;
  }
  const target = candidates[candidates.length - 1];

  if (existingScores && existingScores.getSheetId() !== target.getSheetId()) {
    // If a stub Scores tab exists (from setupSheets), delete it so we can rename cleanly.
    if (existingScores.getLastRow() <= 1) {
      ss.deleteSheet(existingScores);
    } else {
      // Already-populated Scores — leave both, let the operator merge manually.
      Logger.log('An existing Scores tab has data. Rename the Form Responses tab manually.');
      return;
    }
  }
  target.setName('Scores');
  Logger.log('Renamed Form-responses tab → Scores.');
}
