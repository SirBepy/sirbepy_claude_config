---
name: readme
description: Triggers on /readme only.
---

# /readme

> Generate or update README.md for the project.

## Workflow

### Step 1 - Gather context

Check for the following, in order. Use what exists, skip what doesn't:

- `.portfolio-data/metadata.json` - title, shortDescription, liveUrl, mainImage, type, frameworks, languages
- `.portfolio-data/PORTFOLIO.md` - The What, The Why, The How sections
- `.portfolio-data/screenshot-1.png` or any screenshot - for embedding
- `assets/images/favicon.png` or `favicon.svg` - for project icon at top
- `git remote get-url origin` - to construct the GitHub Actions badge and Pages URL
- `CLAUDE.md` - for project type and deploy info

### Step 2 - Construct badges

From the remote URL, extract `username` and `repo`.

Always include:

- Deploy status badge (only if deploy: github-pages in CLAUDE.md or deploy.yml exists):

```
  ![Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)
```

- Last commit badge:

```
  ![Last Commit](https://img.shields.io/github/last-commit/USERNAME/REPO)
```

Optional, include if it adds value:

- Tech stack shields from shields.io based on languages/frameworks in metadata.json
  e.g. `![HTML](https://img.shields.io/badge/HTML-E34F26?logo=html5&logoColor=white)`

### Step 3 - Write README.md

Follow this structure exactly:

```markdown
<!-- TODO: one day consider stylized SVG title headers instead of plain markdown headings -->

<img src="assets/images/favicon.png" width="48" alt="project icon" />

# Project Title

> Short description (from metadata.json shortDescription)

![Deploy](...) ![Last Commit](...) ![HTML](...)

**Live:** https://username.github.io/repo/

---

## About

[The What section from PORTFOLIO.md, or inferred if missing]

[The Why section from PORTFOLIO.md, or inferred if missing]

[The How section from PORTFOLIO.md, only if it exists and has content]

---

## How to run

[Based on project type from CLAUDE.md:

- html: "Open index.html in a browser"
- vite/react: "npm install then npm run dev"
- roblox: relevant Rojo commands
- flutter: "flutter run"]

---

## Project write-up

See [PORTFOLIO.md](.portfolio-data/PORTFOLIO.md) for the full project write-up.
```

Skip any section that has no content. Keep it clean over keeping it complete.

### Step 4 - Confirm

Tell the user what was written and flag any assumptions.
Do not commit - the user handles that.

## Notes

- If README.md already exists, rewrite it fully rather than patching it
- If favicon is SVG only, use the SVG in the img tag instead
- If no portfolio-data exists at all, infer everything from the codebase and flag it
- If remote URL is not set, skip badges and use placeholder for live link
