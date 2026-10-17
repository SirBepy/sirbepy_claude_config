---
name: pretty-readme
description: Makes a repo's GitHub front page look great - banner, badges, icon rows, screenshots, scannable sections.
argument-hint: "[repo path]"
---

# /pretty-readme

> Turn a repo's README into a polished GitHub front page: a real banner, a tight badge row, a
> tech-icon row, screenshots, and sections a stranger can scan in ten seconds.

`/readme` writes a correct README for web projects from portfolio metadata. This skill is the
visual layer: use it when the README already says the right things but looks like a wall of
text, or when a repo is about to go public. It can run on top of a `/readme` result.

No outside skill was adopted for this (searched 2026-10-17: the published "readme generator"
skills only emit text sections, none handle banners, badges or screenshots). The visual pieces
are plain image URLs from long-standing services, so nothing third-party runs in the repo.

## Step 1 - Gather before writing

Read, don't guess. Every claim in the README needs a source read this session.

- Existing `README.md`, `CLAUDE.md`, `docs/`, `PRODUCT.md` / `DESIGN.md` (brand colours, voice).
- Manifests for the real stack and versions (`package.json`, `build.gradle.kts`, `Cargo.toml`,
  `pubspec.yaml`, `plugin.yml`...).
- `git remote get-url origin` for owner/repo (badge and link URLs).
- Existing art: logo, favicon, `og-image`, app icon, screenshots, a live site. A sibling repo
  (the project's website) often has the best art: check it.
- Licence file (badge only if one exists; never invent a licence).

For a monorepo or anything with more than ~5 parts, delegate the per-part summary to one sonnet
Explore subagent with a "cite file:line per fact" report shape, and keep only its table.

## Step 2 - Pick the banner (in this order)

1. **Project art that already exists**: the og-image / social card, a title screen, a logo on a
   real background. Copy it into the repo (`docs/readme/banner.png`, or `.github/` if the repo
   keeps assets there) so the README never depends on another site staying up. Keep it under
   ~500 KB; re-encode a big PNG with Pillow (`optimize=True`, or JPEG/WebP at quality 85).
2. **A screenshot of the running thing** (app, site, game), shot via an isolated Playwright
   browser, never the dev's live windows. Wide crop, roughly 2:1 to 3:1.
3. **capsule-render** only as a fallback when there is no art at all:
   `https://capsule-render.vercel.app/api?type=waving&height=180&color=0:<hex1>,100:<hex2>&text=<Title>&fontColor=ffffff&fontAlignY=38&section=header`
   Take `<hex1>`/`<hex2>` from the project's own palette (DESIGN.md, CSS variables, logo).

Banner goes first, full width, linked to the live site if there is one:

```html
<p align="center">
  <a href="https://example.com"><img src="docs/readme/banner.png" alt="Project title screen" width="100%"></a>
</p>
```

## Step 3 - Header block

Centered, in this order, nothing else above the first section:

1. One-line tagline in bold (what it is + who it's for, under 15 words).
2. A link row to the things a visitor actually wants: live site, download, docs, join address.
   Separate with ` · `.
3. One badge row, **4-7 badges max**. Pick from: build/CI status, latest release/version, the
   core platform version (e.g. Minecraft, Node, Flutter), language, licence, last commit, a live
   status badge if a service exists for it. Use `style=for-the-badge` for one row of big badges
   or `flat-square` for more, never mix styles. Colours from the project palette.
   - Static: `https://img.shields.io/badge/<label>-<message>-<hex>?style=for-the-badge&logo=<simpleicons-slug>&logoColor=white`
     (escape `-` as `--`, `_` as `__`, space as `%20` in label/message).
   - Dynamic: `https://img.shields.io/github/last-commit/<owner>/<repo>?style=...`,
     `.../github/actions/workflow/status/<owner>/<repo>/<file>.yml`, `.../github/v/release/...`.
4. Optional tech row: `https://skillicons.dev/icons?i=java,gradle,js,python&perline=8` (only
   slugs listed on skillicons.dev; verify each slug renders by fetching the URL once).

## Step 4 - Body

Write for a stranger first, a contributor second:

- **What is this** - 2-4 sentences, plain words, no internal jargon.
- **Highlights / features** - a table or a 2-3 column grid, one emoji or small icon + bold name +
  one sentence each. For a monorepo, one row per module, grouped (player-facing, infrastructure).
- **Screenshots** - 2-4 images, side by side in a `<table>` or `<p align="center">` with
  `width="49%"`, each with a one-line caption. Real ones only.
- **Getting started / how to use** - the shortest path to running or joining it. Commands in
  fenced code blocks.
- **Project layout** - a short tree or table for anything with more than a few folders.
- **Development / testing** - the real commands from the manifests.
- **Credits / licence** - credit third-party art and libraries already credited elsewhere.
- Long reference material goes in `<details><summary>...</summary>` blocks or stays in `docs/`
  with a link. Never delete accurate dev documentation from an existing README: move it below
  the fold or into a collapsible block.

## Step 5 - GitHub rendering rules

- GitHub strips `<style>`, `class`, `style=` and scripts. Layout is only `align`, `width`,
  `<table>`, `<p>`, `<details>`, `<picture>`, `<br>`.
- Dark/light art: `<picture><source media="(prefers-color-scheme: dark)" srcset="..."><img src="..."></picture>`.
- Relative image paths resolve against the README's own folder, on the default branch.
- Alt text on every image. Headings in order (one `#` title, then `##`).
- Mermaid diagrams render natively (```mermaid) if a flow diagram helps.
- No em dashes (global rule).

## Step 6 - Verify the render

1. Every image URL returns 200: `curl -s -o /dev/null -w "%{http_code}" <url>` for remote ones,
   file exists for relative ones.
2. Render the markdown and look at it before calling it done: `gh api markdown -F text=@README.md -f mode=gfm -f context=<owner>/<repo>`
   (`-F`, not `-f`: only `-F` reads `@file`)
   into a scratch HTML file under `.for_bepy/`, wrap it with GitHub's CSS
   (`https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-dark.min.css`,
   `<article class="markdown-body">`), and screenshot it with an isolated Playwright browser
   into `.for_bepy/screenshots/<id>/` (id from `~/.claude/skills/close/rename-session.ps1 -GetId`).
   Relative images in that scratch render need `<base href="file:///<repo root>/">`.
3. Show the screenshot to the dev (Read it back, or `/preview`), then commit via `/commit`.

## Step 7 - Repo page extras (ask before changing)

These live outside the README and are outward-facing, so confirm with the dev first:

- About box: `gh repo edit --description "..." --homepage <url> --add-topic <t>` (5-10 topics).
- Social preview image: no API exists; tell the dev the exact file to upload in Settings > General.
- Visibility: going public publishes the whole git history. Run a full-history secret and
  personal-data scan (subagent) and get an explicit OK before `gh repo edit --visibility public --accept-visibility-change-consequences`.
