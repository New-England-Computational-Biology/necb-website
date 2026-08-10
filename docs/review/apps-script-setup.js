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
  'Andrew Caruso', 'Curie Cha', 'Kit Gallagher', 'Aditya Gorla',
  'Lei Huang', 'Senbao Lu', 'Karna Mendonca', 'Zain Patel',
  'Ben Perry', 'Anna Sappington', 'Kristen Severson', 'Ross Stewart',
  'Ruohan Wang', 'Will White', 'Laura Yeoh', 'Nanxiang (Sam) Zhao'
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

/* ---------- Submissions ---------- */
function setupSubmissions_(ss) {
  const sh = getOrCreate_(ss, 'Submissions');
  sh.clear();

  const headers = [
    'abstract_id', 'title', 'authors', 'presenting_affiliation',
    'abstract_text', 'pdf_link', 'topic_keywords', 'chair_notes'
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
  sh.setColumnWidths(8, 1, 240);  // chair_notes

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
    'coi_flag', 'status', 'pdf_link'
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

  // Fill formulas for rows 2..500 (bump if you expect more assignments)
  const N = 500;
  const rng = sh.getRange(2, 2, N, 1);
  const formulas = Array.from({ length: N }, (_, i) => {
    const row = i + 2;
    return [`=IFERROR(VLOOKUP(A${row}, Submissions!A:F, 2, FALSE),)`];
  });
  rng.setFormulas(formulas);

  const rng3 = sh.getRange(2, 3, N, 1);
  rng3.setFormulas(Array.from({ length: N }, (_, i) => {
    const row = i + 2;
    return [`=IFERROR(VLOOKUP(A${row}, Submissions!A:G, 7, FALSE),)`];
  }));

  const rng7 = sh.getRange(2, 7, N, 1);
  rng7.setFormulas(Array.from({ length: N }, (_, i) => {
    const row = i + 2;
    return [`=IFERROR(VLOOKUP(A${row}, Submissions!A:F, 6, FALSE),)`];
  }));

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
    .setRanges([sh.getRange(2, 1, N, 7)])
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
    'abstract_id', 'n_reviews',
    'mean_significance', 'mean_rigor', 'mean_clarity', 'mean_fit',
    'n_talk', 'n_poster', 'n_reject',
    'mean_overall', 'mean_confidence', 'weighted_score',
    'disagreement_flag', 'rationales'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  styleHeader_(sh, headers.length);
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, 1, 100);
  sh.setColumnWidths(2, 1, 80);
  sh.setColumnWidths(3, 4, 110);
  sh.setColumnWidths(7, 3, 70);
  sh.setColumnWidths(10, 3, 130);
  sh.setColumnWidths(13, 1, 160);
  sh.setColumnWidths(14, 1, 500);

  // A2 spills the unique abstract IDs from Scores; B-N compute per-abstract
  sh.getRange('A2').setFormula(
    `=IFERROR(SORT(UNIQUE(FILTER(Scores!C2:C, Scores!C2:C<>""))),)`
  );

  // Row-2 formulas that spread down as new abstracts show up
  // (We use per-row array formulas anchored to A:A so they extend automatically.)
  const perRow = [
    // B: n_reviews
    `=IF(A2="","",COUNTIF(Scores!C:C, A2))`,
    // C: mean_significance
    `=IF(A2="","",IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!D:D),))`,
    // D: mean_rigor
    `=IF(A2="","",IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!E:E),))`,
    // E: mean_clarity
    `=IF(A2="","",IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!F:F),))`,
    // F: mean_fit
    `=IF(A2="","",IFERROR(AVERAGEIF(Scores!C:C, A2, Scores!G:G),))`,
    // G: n_talk
    `=IF(A2="","",COUNTIFS(Scores!C:C, A2, Scores!H:H, "Accept as talk"))`,
    // H: n_poster
    `=IF(A2="","",COUNTIFS(Scores!C:C, A2, Scores!H:H, "Accept as poster"))`,
    // I: n_reject
    `=IF(A2="","",COUNTIFS(Scores!C:C, A2, Scores!H:H, "Reject"))`,
    // J: mean_overall
    `=IF(OR(A2="",B2=0),,IFERROR((G2*3+H2*2+I2*1)/B2,))`,
    // K: mean_confidence
    `=IF(OR(A2="",B2=0),,IFERROR((COUNTIFS(Scores!C:C,A2,Scores!I:I,"Low")*1+COUNTIFS(Scores!C:C,A2,Scores!I:I,"Med")*2+COUNTIFS(Scores!C:C,A2,Scores!I:I,"High")*3)/B2,))`,
    // L: weighted_score
    `=IF(OR(J2="",K2=""),,J2*K2)`,
    // M: disagreement_flag
    `=IF(A2="","",IF(AND(G2>0,I2>0),"talk_vs_reject",""))`,
    // N: rationales
    `=IF(A2="","",TEXTJOIN(" | ", TRUE, FILTER(Scores!J:J, Scores!C:C=A2)))`
  ];

  const N = 500;
  perRow.forEach((formula, colIdx) => {
    const col = colIdx + 2; // B..N → 2..14
    const rng = sh.getRange(2, col, N, 1);
    const arr = [];
    for (let r = 0; r < N; r++) {
      arr.push([formula.replace(/2/g, String(r + 2))]);
    }
    rng.setFormulas(arr);
  });

  // Format numeric columns to 2 decimals
  sh.getRange(2, 3, N, 4).setNumberFormat('0.00');
  sh.getRange(2, 10, N, 3).setNumberFormat('0.00');

  // Highlight disagreements
  const flagFormat = SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains('_')
    .setBackground('#F4C7C3')
    .setFontColor('#8B0000')
    .setRanges([sh.getRange(2, 13, N, 1)])
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
