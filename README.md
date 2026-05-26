# NECB 2026 — Conference Website

Static landing site for the **New England Computational Biology Symposium 2026** (Oct 1–2, 2026, Cambridge, MA).

Built with [Hugo](https://gohugo.io/) (extended). No external theme — the entire site is in this repo, so it's easy to customize without learning a third-party framework.

## Quick start

```bash
# 1. install Hugo extended (one-time)
#    macOS:    brew install hugo
#    Linux:    snap install hugo  (or download from https://github.com/gohugoio/hugo/releases)
#    conda:    conda install -c conda-forge hugo

# 2. preview locally
hugo server -D

# Visit http://localhost:1313
```

## Project layout

```
necb-website/
├── config/_default/hugo.yaml    # site config + nav + theme params
├── content/_index.md             # landing page (just metadata; layout drives content)
├── data/                         # editable content: organizers, themes, program, key dates
│   ├── organizers.yaml
│   ├── themes.yaml
│   ├── program.yaml
│   └── keyDates.yaml
├── layouts/
│   ├── _default/baseof.html      # HTML shell (head, navbar, footer)
│   ├── index.html                # homepage composition
│   └── partials/
│       ├── navbar.html
│       ├── footer.html
│       └── sections/             # one HTML partial per page section
├── assets/css/main.css           # all styling, palette C ("Modern Bio-Tech")
├── static/img/                   # logo, favicon
├── static/js/nav.js              # mobile nav toggle
├── .github/workflows/deploy.yml  # builds with Hugo + publishes to GitHub Pages
├── static/CNAME                  # custom domain (newenglandcompbio.org)
└── .gitignore
```

## How to edit content

Most edits are in `data/*.yaml` — no HTML required.

| Want to change… | Edit this file |
|---|---|
| Conference dates / venue text / contact email | `config/_default/hugo.yaml` (`params:` block) |
| Themes (cards under "Themes") | `data/themes.yaml` |
| Draft program | `data/program.yaml` |
| Key dates table | `data/keyDates.yaml` |
| Organizer lists (Co-Chairs, Steering, Organizing) | `data/organizers.yaml` |
| Hero copy or section text | `layouts/partials/sections/*.html` |
| Colors / styling | `assets/css/main.css` (CSS variables at the top) |
| Logo / favicon | `static/img/logo.svg`, `static/img/favicon.svg` |

When ISCB registration is ready: set `params.registrationURL` in `config/_default/hugo.yaml` — the hero button switches from the "coming soon" badge to a real Register link automatically.

## Branding

- **Palette C — Modern Bio-Tech**
  - Indigo `#1E3A8A` (primary)
  - Bio-green `#10B981` (accent)
  - Off-white `#F8FAFC` (background)
  - Slate `#1F2937` (body text)
- **Typography**: Inter (UI) + Lora (display), loaded from Google Fonts
- **Logo**: placeholder SVG wordmark — easy to swap once a designer delivers a final mark

## Deploy

The site is deployed automatically to **GitHub Pages** on every push to `main` by
`.github/workflows/deploy.yml` (installs Hugo extended, runs `hugo --gc --minify`,
publishes `public/`). The custom domain `newenglandcompbio.org` is configured via
`static/CNAME`.

To deploy a change: edit, commit, push to `main` — the Action does the rest.
Watch runs at https://github.com/New-England-Computational-Biology/necb-website/actions.

## Open items / TBD

- [ ] Confirm public conference name
- [ ] Add real affiliations in `data/organizers.yaml`
- [ ] Replace placeholder logo with a designed mark
- [ ] Replace `necb2026@example.org` with the real contact alias in `config/_default/hugo.yaml`
- [ ] Add speakers to a new `data/speakers.yaml` once they're confirmed (and update `layouts/partials/sections/speakers.html` to read from it)
- [ ] Fill in key dates as they're set
- [ ] Hook up registration URL when ISCB link is ready
- [ ] Add a `code-of-conduct.md` page; the footer link is currently an anchor stub

## Why not the full Hugo Blox / Wowchemy framework?

The plan called for Hugo Blox, but the full framework brings in Go modules and Node.js
dependencies that complicate a simple landing page. This site uses Hugo's native layouts
and partials directly — same end result, but ~10x simpler to maintain, deploy, and hand off.
If we later need Blox-specific widgets, the content (Markdown + YAML data files) ports over
cleanly.
