/**
 * NECB 2026 · Reviewer Queue — one-shot setup.
 *
 * Purpose: build a REVIEWER-FACING spreadsheet that mirrors just the two tabs
 * reviewers need (Assignments + Submissions) from the master sheet via
 * IMPORTRANGE. Chairs keep the master private; reviewers only see this mirror.
 *
 * How to use:
 *   1. Create a new empty Google Sheet, name it "NECB 2026 · Reviewer Queue".
 *   2. Copy its sheet ID from the URL into REVIEWER_SHEET_ID below.
 *   3. Extensions → Apps Script → paste this file's contents.
 *   4. Enable Sheets Advanced Service: sidebar → Services (+) → Google Sheets API.
 *   5. Save. From the function picker, run `setupReviewerQueue`.
 *   6. Return to the sheet. The two IMPORTRANGE cells show "You need to grant
 *      access" — hover cell A1 on each tab, click Allow access. (One-time.)
 *   7. Once data loads (few seconds), run `generateReviewerFilterViews` to
 *      create the 26 filter views + Reviewer URLs tab.
 *   8. Share the sheet with reviewers as Viewer. Copy filter-view URLs into
 *      the kickoff emails.
 */

const MASTER_SHEET_ID   = '1WSe1ONckffM-SBeBWpoZN-FORCF2LC1ZHB9ljG_dLSY';
const REVIEWER_SHEET_ID = 'PASTE_NEW_SHEET_ID';

const REVIEWERS = [
  'Ritwik Anand', 'Andrew Caruso', 'Curie Cha', 'Xiwei Cheng', 'Kishalay Das',
  'Kit Gallagher', 'Jocelyn Garcia', 'Aditya Gorla', 'Lei Huang',
  'Benjamin Jones', 'Panos Ketonis', 'Anurendra Kumar', 'Senbao Lu',
  'Karna Mendonca', 'Zain Patel', 'Ben Perry', 'Anna Sappington',
  'Kristen Severson', 'Ross Stewart', 'Siddharth Viswanath', 'Ruohan Wang',
  'Will White', 'Ke Xu', 'Laura Yeoh', 'Yikun Zhang', 'Nanxiang (Sam) Zhao'
];

/* ---------- One-shot setup ---------- */
function setupReviewerQueue() {
  const ss = SpreadsheetApp.openById(REVIEWER_SHEET_ID);

  const assignments = getOrCreate_(ss, 'Assignments');
  assignments.clear();
  assignments.getRange('A1').setFormula(
    `=IMPORTRANGE("${MASTER_SHEET_ID}", "Assignments!A1:H1000")`
  );
  assignments.setFrozenRows(1);
  assignments.setColumnWidths(1, 1, 90);
  assignments.setColumnWidths(2, 1, 320);
  assignments.setColumnWidths(3, 1, 220);
  assignments.setColumnWidths(4, 1, 200);
  assignments.setColumnWidths(5, 1, 80);
  assignments.setColumnWidths(6, 1, 110);
  assignments.setColumnWidths(7, 1, 260);
  assignments.setColumnWidths(8, 1, 110);

  const submissions = getOrCreate_(ss, 'Submissions');
  submissions.clear();
  submissions.getRange('A1').setFormula(
    `=IMPORTRANGE("${MASTER_SHEET_ID}", "Submissions!A1:H1000")`
  );
  submissions.setFrozenRows(1);
  submissions.setColumnWidths(1, 1, 90);
  submissions.setColumnWidths(2, 1, 320);
  submissions.setColumnWidths(3, 1, 260);
  submissions.setColumnWidths(4, 1, 220);
  submissions.setColumnWidths(5, 1, 420);
  submissions.setColumnWidths(6, 1, 260);
  submissions.setColumnWidths(7, 1, 220);
  submissions.setColumnWidths(8, 1, 240);

  // Delete default Sheet1 if it's still there and empty.
  const def = ss.getSheetByName('Sheet1');
  if (def && ss.getSheets().length > 1) ss.deleteSheet(def);

  SpreadsheetApp.getUi().alert(
    'Reviewer Queue: two tabs created with IMPORTRANGE formulas.\n\n' +
    'Next: return to each tab and click "Allow access" on cell A1 to grant\n' +
    'permission to pull from the master sheet. Then run generateReviewerFilterViews.'
  );
}

/* ---------- Per-reviewer filter views on the mirror sheet ---------- */
function generateReviewerFilterViews() {
  const ss = SpreadsheetApp.openById(REVIEWER_SHEET_ID);
  const assignments = ss.getSheetByName('Assignments');
  if (!assignments) {
    SpreadsheetApp.getUi().alert('No Assignments tab. Run setupReviewerQueue first.');
    return;
  }

  const meta = Sheets.Spreadsheets.get(REVIEWER_SHEET_ID, {
    fields: 'sheets(properties(sheetId,title),filterViews(filterViewId,title))',
  });
  const sheetMeta = meta.sheets.find(s => s.properties.title === 'Assignments');
  const sheetId = sheetMeta.properties.sheetId;

  // Clean any prior "Queue — " filter views
  const oldFilters = sheetMeta.filterViews || [];
  const deleteRequests = oldFilters
    .filter(fv => fv.title && fv.title.startsWith('Queue — '))
    .map(fv => ({ deleteFilterView: { filterId: fv.filterViewId } }));
  if (deleteRequests.length) {
    Sheets.Spreadsheets.batchUpdate({ requests: deleteRequests }, REVIEWER_SHEET_ID);
  }

  const addRequests = REVIEWERS.map(reviewer => ({
    addFilterView: {
      filter: {
        title: `Queue — ${reviewer}`,
        range: {
          sheetId: sheetId,
          startRowIndex: 0,
          endRowIndex: 1001,
          startColumnIndex: 0,
          endColumnIndex: 8,
        },
        criteria: {
          '3': {  // reviewer column D
            condition: {
              type: 'TEXT_EQ',
              values: [{ userEnteredValue: reviewer }],
            },
          },
          '4': {  // coi_flag column E — hide TRUE
            hiddenValues: ['TRUE'],
          },
        },
      },
    },
  }));

  const resp = Sheets.Spreadsheets.batchUpdate({ requests: addRequests }, REVIEWER_SHEET_ID);
  const replies = resp.replies || [];

  const urls = [];
  for (let i = 0; i < REVIEWERS.length; i++) {
    const fvid = replies[i].addFilterView.filter.filterViewId;
    const url = `https://docs.google.com/spreadsheets/d/${REVIEWER_SHEET_ID}/edit?gid=${sheetId}&fvid=${fvid}`;
    urls.push([REVIEWERS[i], url]);
    Logger.log(`${REVIEWERS[i]}\t${url}`);
  }

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

  // Optional: hide the URLs tab from reviewers to reduce clutter
  urlSheet.hideSheet();

  SpreadsheetApp.getUi().alert(
    `Generated ${REVIEWERS.length} filter views on the Reviewer Queue.\n\n` +
    `URLs are on the (hidden) "Reviewer URLs" tab — un-hide via View → Hidden sheets ` +
    `to copy them into the kickoff email.`
  );
}

/* ---------- Helper ---------- */
function getOrCreate_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}
