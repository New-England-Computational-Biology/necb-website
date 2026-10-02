/**
 * NECB 2026 · post-event feedback form.
 *
 * Creates a Google Form (~3 minutes, collects respondents' email) and a linked response sheet,
 * then logs the public link to paste into the feedback email
 * (docs/review/feedback-email.md).
 *
 * Run once:
 *   1. Go to https://script.google.com → New project, signed in as
 *      newenglandcompbio@gmail.com.
 *   2. Paste this file into Code.gs and save.
 *   3. Run `createFeedbackForm` and grant the Forms/Drive/Sheets permissions.
 *   4. View → Logs (or Execution log) shows the edit URL, the public link and
 *      the response sheet URL.
 */

function createFeedbackForm() {
  const form = FormApp.create('NECB 2026 · Feedback');
  form
    .setTitle('NECB 2026 · Feedback')
    .setDescription(
      'Thank you for joining the New England Computational Biology Symposium ' +
      '(October 1–2, 2026, Microsoft Research New England). This takes about ' +
      '3 minutes. ' +
      'Your answers will shape NECB 2027.')
    // Ask every respondent for their email (Settings → Responses → Collect email addresses).
    .setCollectEmail(true)
    .setLimitOneResponsePerUser(false)
    .setAllowResponseEdits(false)
    .setProgressBar(true)
    .setConfirmationMessage('Thank you! We hope to see you at NECB 2027.');

  // --- Overall
  form.addScaleItem()
    .setTitle('Overall, how would you rate NECB 2026?')
    .setBounds(1, 5).setLabels('Poor', 'Excellent')
    .setRequired(true);

  form.addScaleItem()
    .setTitle('How likely are you to recommend NECB to a colleague?')
    .setBounds(0, 10).setLabels('Not at all likely', 'Extremely likely');

  // --- Program and logistics
  form.addGridItem()
    .setTitle('How would you rate each part of NECB?')
    .setRows([
      'Keynote talks',
      'Invited talks',
      'Selected talks',
      'Poster sessions',
      'Networking and conversations',
      'Venue (Microsoft Research)',
      'Food and coffee',
      'Registration and check-in',
      'Website and program book',
      'MIT FutureFest Salon',
    ])
    .setColumns(['Excellent', 'Good', 'Fair', 'Poor', 'N/A']);

  // --- About you
  form.addCheckboxItem()
    .setTitle('Which parts did you attend?')
    .setChoiceValues([
      'Thursday, October 1',
      'Friday, October 2',
      'MIT FutureFest Salon (Thursday evening)',
    ]);

  form.addMultipleChoiceItem()
    .setTitle('What best describes you?')
    .setChoiceValues([
      'Undergraduate student',
      'Graduate student',
      'Postdoc',
      'Faculty / principal investigator',
      'Research staff',
      'Industry',
    ])
    .showOtherOption(true);

  form.addMultipleChoiceItem()
    .setTitle('Did you present at NECB 2026?')
    .setChoiceValues(['Yes, a talk', 'Yes, a poster', 'No']);

  // --- Open questions
  form.addParagraphTextItem()
    .setTitle('What was the most valuable part of NECB 2026 for you?');

  form.addParagraphTextItem()
    .setTitle('What should we change, add or drop next year?');

  form.addParagraphTextItem()
    .setTitle('Which topics or speakers would you like to see at NECB 2027?');

  // --- Next year
  form.addMultipleChoiceItem()
    .setTitle('Would you attend NECB 2027?')
    .setChoiceValues(['Yes', 'Maybe', 'No']);

  form.addCheckboxItem()
    .setTitle('Would you like to get involved next year?')
    .setChoiceValues([
      'Review abstracts',
      'Volunteer at the event',
      'Help organize',
      'Sponsor or host',
    ]);

  // Responses land in a new spreadsheet next to the form.
  const ss = SpreadsheetApp.create('NECB 2026 · Feedback (responses)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  Logger.log('Edit form:      ' + form.getEditUrl());
  Logger.log('Public link:    ' + form.getPublishedUrl());
  Logger.log('Short link:     ' + form.shortenFormUrl(form.getPublishedUrl()));
  Logger.log('Response sheet: ' + ss.getUrl());
}
