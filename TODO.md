# NECB 2026 — Open tasks

Living list of items still pending on the conference website. Sorted by category, not priority. Cross-link to commits / PRs / issues as they land.

## Awaiting committee decisions

- [ ] **Registration platform** — currently neither ISCB nor Eventbrite is confirmed. Decide between:
  - **ISCB** — assumed in early planning notes; reaching out is still TBD
  - **Eventbrite** — alternative being considered
  - Once decided, update the hero CTA from "Registration — coming soon" to the actual sign-up link via `params.registrationURL` in `config/_default/hugo.yaml`. Also re-add platform mention to the About section if relevant.
- [ ] **Abstract submission via OpenReview** — platform chosen, but the venue/instance isn't set up yet. Once live, set `params.abstractURL` in `config/_default/hugo.yaml`; the hero badge will automatically switch from "coming soon" to a Submit-abstract link.
- [ ] **Poster award funding** — currently the About section says "We plan to recognize outstanding poster presentations." Until a sponsor commits, the language stays aspirational. Update the copy once funding lands.
- [ ] **Real key dates** — every row in `data/keyDates.yaml` except the conference itself is "TBA". Fill in: abstract submission opens / deadline / author notifications / registration opens / early-bird ends.
- [ ] **Trainees group** — `data/organizers.yaml` has `trainees:` with empty members; the section won't render until names are added.
- [ ] **Friends of the conference** — only Jason Buenrostro is listed; committee notes hinted at a second name ("both had limited bandwidth…"). Confirm and add.
- [ ] **Speakers** — placeholder section only. Once a keynote is confirmed, add `data/speakers.yaml` and a partial that reads from it (mirror the organizers pattern).
- [ ] **Sponsors** — keep the CTA-only treatment until first sponsor contracts. Then add `data/sponsors.yaml` and a logos row.

## Content polish

- [ ] **Social handles** — `params.social.{twitter,linkedin,github}` are empty in `config/_default/hugo.yaml`. Footer/header doesn't surface them yet; once a handle exists, wire it up.
- [ ] **Code of Conduct** — footer link is currently `#`. Either write a page (e.g., `content/code-of-conduct.md`) or remove the link until one exists.
- [ ] **Affiliations** — the disclaimer "Affiliations will be added as committee members confirm" is intentionally kept because some affiliations may still be provisional. Drop the disclaimer once everyone has confirmed final affiliation.

## Visual / design

- [ ] **Logo** — current `static/img/logo.svg` is an explicit placeholder wordmark. Design polish brief is at `/Users/lp698/.claude/plans/now-can-you-give-silly-thacker.md` — pass to Claude Design when ready.
- [ ] **og-image.png** — `params.ogImage: img/og-image.png` is referenced in config but the file doesn't exist. Link previews on Twitter/LinkedIn/Slack are currently broken. Generate a 1200×630 PNG.
- [ ] **Favicon** — placeholder SVG; replace alongside the logo redesign.
- [ ] **Hero / sections polish** — see design brief.

## Technical debt

- [ ] **Hugo deprecation warnings** — `.Site.LanguageCode` and `.Site.Data` (and the `languageCode` config key) are deprecated in Hugo 0.158+. Build still passes at 0.162, but will break on a future major version. Update `layouts/_default/baseof.html` and the partials that reference `site.Data.*`.
- [ ] **GitHub Actions Node.js 20 → 24** — currently using `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` as a workaround. Once `actions/checkout`, `actions/configure-pages`, `actions/upload-pages-artifact`, and `actions/deploy-pages` ship native Node 24 versions, drop the env override.

## Logistics (not website-blocking, but related)

- [ ] **Gmail mailbox** — confirm `newenglandcompbio@gmail.com` is set up and monitored. The address is live across the site (`mailto:` links, sponsor CTA, contact section).
- [ ] **Travel / hotel info** — venue section promises "Detailed travel directions, accommodation suggestions, and special-rate hotel information will be posted here closer to the conference dates." Add when ready.
- [ ] **Optional shared-housing channel** — meeting notes mention "Piazza discussion group so they can find potential shared accommodations / shared rides". Add a link in venue section if/when it exists.

## Done (for reference)

- [x] Migrate prototype from `ivazquez/necb-website` (private) to `New-England-Computational-Biology/necb-website` (public)
- [x] Switch hosting from Netlify to GitHub Pages with automated deploys
- [x] Custom domain `newenglandcompbio.org` with HTTPS enforced and Let's Encrypt cert
- [x] Archive the duplicate `necb2026` repo
- [x] Strip unconfirmed ISCB language from the site until partnership is confirmed
- [x] Add OpenReview abstract CTA in the hero
- [x] Real contact email (`newenglandcompbio@gmail.com`)
- [x] Soften unfunded poster-award claim
- [x] Remove unconfirmed 350-attendee capacity figure
- [x] Add Founding Chairs (Pedja, Luca) and Friends of the conference (Jason Buenrostro) groups
- [x] Add empty Trainees group structure for future population
