# Web project setup

The standard for a new web/HTML project (plain HTML, Vite, CRA). `/bepy-project-setup-web` reads this file and runs the
runnable skills at the right points; everything else here is guidance Claude applies by hand. Replaces the old
`/init-claude-md`, `/meta-tags`, `/readme`, `/apply-styleguide` and `/inject-widgets` skills (deleted 2026-11-08: zero use in
65 days, no script or template that a doc cannot carry).

Runnable skills that stay: `/favicon` (scripts), `/update-workflow` (deploy.yml templates), `/github-pages-init`,
`/portfolio-data` (writes `.portfolio-data/metadata.json`, consumed outside this repo), `/pwa`, `/screenshot`,
`/pretty-readme`, `/deploy`.

## Step order

The order is load-bearing: later steps read what earlier ones write.

0. **Git.** `git init` on `main` when not a repo; if `.gitignore` is missing, create one with `.DS_Store`, `node_modules/`,
   `dist/`, `.env`; with files and no commits yet, `/commit` with a `CHORE:` prefix.
1. **CLAUDE.md** (below). Later steps read its `Type:` line.
2. `/favicon`
3. `/update-workflow`. `/github-pages-init` warns when `deploy.yml` is missing.
4. `/github-pages-init`. Creates the GitHub remote; meta tags and README derive the Pages URL and badges from
   `git remote get-url origin`, so the remote has to exist before steps 8 and 9.
5. **Widgets** (below).
6. **Styleguide** (below).
7. `/portfolio-data`. After the styleguide so its screenshots show the final look; before steps 8 and 9, which read
   `.portfolio-data/metadata.json` and `PORTFOLIO.md`.
8. **Meta tags** (below).
9. **README** (below).
10. `/pwa`, unless the dev said to skip it.

Commit once at the end with `CHORE: bepy project setup`. Never push. Default is run everything; the dev can name steps to
skip, or ask to pick, in which case ask one multi-select question of which to skip.

## 1. CLAUDE.md

Reader is Claude Code, not a human: include anything that takes several files to discover, omit what one read shows.
Write at the project root; when one exists, update it to this structure and keep what is project-specific.

```markdown
## Project

One sentence: what this app does and who it's for.

Type: html | vite | react | roblox | flutter | tauri | other
Deploy: github-pages | none | other

## Structure

One-liner of the source layout.

## Commands

- Dev: `<dev command>`
- Verify: `<build or type-check command>`
- Test: `<test command>` (only if the project has one)

## Architecture

(omit for simple projects; for several subsystems or non-obvious boundaries, the file map and data flow)

## Rules

- project-specific rules Claude could not know otherwise
```

`Type:` is a bare enum value, no parenthetical (`Type: vite`, not `Type: vite (7 + React 19)`); elaboration goes in the
description sentence. `/update-workflow`, `/github-pages-init`, `/pwa` read it.

| Value | When |
| --- | --- |
| `html` | plain HTML/CSS/JS, no build step |
| `vite` | any Vite project, including Vite + React |
| `react` | Create React App only (builds to `build/`) |
| `roblox` | Roblox Luau |
| `flutter` | Flutter/Dart |
| `tauri` | Tauri desktop |
| `other` | anything else |

Rule test: "would Claude need to open a file to know this?" Yes: include. No: omit. Skip anything in the global CLAUDE.md.

## 5. Widgets

Add before `</body>` of `index.html`, settings widget first, unless already present:

```html
<!-- Settings widget - comment out to disable -->
<script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@cb6aebd1b672d69bae3aff91581a0a6c6ab2e695/widget/settings.js" integrity="sha384-XqnpxRCwFEPZrWuLruU+i5GGSEgUckkuK/Yw2lh2ft9Wj/lYPnXvDyHxHdpyJD3k" crossorigin="anonymous"></script>
<!-- Animated background. To disable: set window.BEPY_BACKGROUND = false before this tag. To use a custom SVG: set window.BEPY_BG_PATTERN = 'your-pattern.svg' before this tag. -->
<script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@cb6aebd1b672d69bae3aff91581a0a6c6ab2e695/widget/background.js" integrity="sha384-0icxjbauzIJXB+EZsImSSwXo+42rqrV61xvOKHFNcJURAs0hZeCc587J5gUeeTP3" crossorigin="anonymous"></script>
```

Both are pinned to commit `cb6aebd1b672d69bae3aff91581a0a6c6ab2e695`. A pin bump without recomputing SRI makes every
project silently reject the load: recompute both hashes (SHA384 over the fetched file bytes) in the same edit as any bump.

The widget renders top-right. If a page element already sits fixed or absolute in that corner, move the page element below
it, using the widget's measured bounding box as the offset, never a guessed value.

## 6. Styleguide

Source: `https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css`. Link it in `<head>` before any project
stylesheet so project styles override it:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css" />
```

Read the project's CSS wherever it lives: glob `**/*.css` excluding `node_modules/`, `dist/`, `build/`, `.next/`. A hardcoded
`src/styles/` silently reviews nothing in other layouts. Replace hardcoded values with vars:

| Hardcoded | Replace with |
| --- | --- |
| Background colors | `var(--color-background)`, `var(--color-surface)`, `var(--color-surface-alt)` |
| Text colors | `var(--color-text)`, `var(--color-text-muted)` |
| Accent colors | `var(--color-primary)`, `var(--color-secondary)` |
| Border colors | `var(--color-border)` |
| Font families | `var(--font-body)`, `var(--font-heading)`, `var(--font-mono)` |
| Border radius | `var(--radius-card)`, `var(--radius-badge)` |
| Box shadows | `var(--shadow-card)` |

Pick the closest semantic match, not the closest color value. Remove `background` / `background-color` from `body` and `html`
(the animated background script owns it). Then add standard classes to HTML, never removing existing layout classes:
cards -> `.card` / `.card-alt`; buttons -> `.btn` + `.btn-primary` / `.btn-outline` / `.btn-ghost`; badges -> `.badge`,
`.badge-tech`, `.badge-success`, `.badge-info`; inputs, selects, textareas -> `.input`. Finish with a summary of what changed
and what was ambiguous. Python desktop (pywebview) projects: `refs/styleguide-pywebview.md`.

## 8. Meta tags

All six inside `<head>` of `index.html`, grouped after existing meta tags, adding only the missing ones:

```html
<meta name="description" content="..." />
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="https://USER.github.io/REPO/assets/images/favicon.png" />
<meta property="og:url" content="https://USER.github.io/REPO/" />
<meta name="twitter:card" content="summary" />
```

Sources: `.portfolio-data/metadata.json` (`title`, `shortDescription`, `mainImage`), else the page `<title>` and the codebase.
The Pages base comes from `git remote get-url origin`. Both URLs must be absolute `https://`; with no remote, omit
`og:image` rather than emit a relative one.

## 9. README

Keep a README that already carries `/pretty-readme` output (banner image, badge or icon row): fix only stale facts (live URL,
run command). Rewriting wipes the visual work. Otherwise write or update this shape, skipping empty sections:

```markdown
<img src="assets/images/favicon.png" width="48" alt="project icon" />

# Project Title

> shortDescription

![Deploy](https://github.com/USER/REPO/actions/workflows/deploy.yml/badge.svg) ![Last Commit](https://img.shields.io/github/last-commit/USER/REPO)

**Live:** https://USER.github.io/REPO/

---

## About
What, Why, How from `.portfolio-data/PORTFOLIO.md`, or inferred and flagged.

## How to run
html: open index.html. vite/react: `npm install` then `npm run dev`. roblox: the Rojo commands. flutter: `flutter run`.

## Project write-up
See [PORTFOLIO.md](.portfolio-data/PORTFOLIO.md).
```

Deploy badge only when `Deploy: github-pages` or a `deploy.yml` exists; tech shields from shields.io when they add value. No
remote: skip badges and leave a placeholder live link. Use the SVG in the icon tag when there is no favicon PNG. Leave no
`<!-- TODO` behind.
