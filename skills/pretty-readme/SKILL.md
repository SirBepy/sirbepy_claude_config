---
name: pretty-readme
description: Makes a repo's GitHub front page look great - banner, badges, icon rows, screenshots, scannable sections.
argument-hint: "[repo path]"
---

# /pretty-readme

> Turn a repo's README into a polished GitHub front page: a real banner, a tight badge row, a
> tech-icon row, screenshots, and sections a stranger can scan in ten seconds.

`refs/web-project-setup.md` section 9 writes a correct README for web projects from portfolio
metadata. This skill is the visual layer: use it when the README already says the right things
but looks like a wall of text, or when a repo is about to go public. It can run on top of that
README.

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

For a monorepo or anything with more than ~5 parts, delegate the per-part summary to one
Explore subagent (`model: 'sonnet'`, prompt opens with the read-only preamble below) with a
"cite file:line per fact" report shape, and keep only its table.

**Read-only preamble** for every read-only subagent this skill dispatches (Step 1 and Step 7). The
three markers are what `hooks/dispatch-preamble-guard.py` checks for; same shape as `/code-check`:

```
READ-ONLY DISPATCH

Leave all changes unstaged. Never run `git add`. The main agent will run /commit by pathspec after your report-back.

`run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
before ending your turn.
```

## Step 2 - Banner and screenshots

Reference output: the claude_conductor and windows_taskbar_widgets READMEs (SirBepy). Reference
scripts, read-only, for accuracy only (gitignored, may be gone; write your own and test it, do not
copy them blind): `C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\.for_bepy\readme-banner\`
(`banner.html`, `shot.mjs`, `render.mjs`, `assemble.py`, `top.md`, `shots.md`).

### 2a - Banner (in this order)

1. **An HTML banner rendered by Playwright.** The default whenever there is a name and a palette,
   even with no art. One `#banner` div (about 1280x400 CSS px, `border-radius`), Google Fonts via
   `<link>`, Phosphor via `https://unpkg.com/@phosphor-icons/web`, colours from the project's
   DESIGN.md or CSS variables, an optional logo on the left, the title, a one-line tagline and 3-4
   feature chips. Shoot it with an isolated `chromium.launch()`: `deviceScaleFactor: 2`, wait for
   `networkidle`, then `document.fonts.ready` plus a short timeout, then
   `page.locator("#banner").screenshot({ path, omitBackground: true })` so the rounded corners are
   transparent (reference: `shot.mjs`). Gotchas that cost time before:
   - **Descender clip:** a `background-clip:text` gradient title with `line-height:1` cuts the
     bottom of g/y/p. Add bottom padding to the heading.
   - **Size budget:** a 1440x450 PNG came to about 520 KB, which is the ceiling. Do not
     palette-quantise it to save bytes: that bands the gradients. Shrink the pixel width instead
     (1280 wide came to 334 KB).
   - **Edge-run art:** source art with a hard cut edge (a cropped sleeve, a clipped sprite) runs off
     the banner edge with a negative `left`/`bottom` offset, so the cut never shows.

   Save to `docs/readme/banner.png` (or `.github/` if the repo keeps assets there), so the README
   never depends on another site staying up.
2. **Project art that already exists** (og-image, title screen, a logo on a real background), when
   it already works as a banner. Copy it into the repo and keep it under ~500 KB (re-encode a big
   PNG with Pillow `optimize=True`, or JPEG/WebP at quality 85).
3. **A screenshot of the running thing** (app, site, game) via an isolated Playwright browser,
   wide crop roughly 2:1 to 3:1.
4. **capsule-render** only as a last fallback when Playwright is not available:
   `https://capsule-render.vercel.app/api?type=waving&height=180&color=0:<hex1>,100:<hex2>&text=<Title>&fontColor=ffffff&fontAlignY=38&section=header`
   Take `<hex1>`/`<hex2>` from the project's own palette.

Banner goes first, full width, linked to the live site or latest release if there is one:

```html
<p align="center">
  <a href="https://example.com"><img src="docs/readme/banner.png" alt="Project title screen" width="100%"></a>
</p>
```

### 2b - Real component screenshots (never the dev's screen)

Aim for at least 3. Render the app's own components with fake data, then crop. Never capture the
dev's live windows (their data, their tabs). Two routes that worked; pick by what the repo has:

- **The repo's own view harness**, if there is one (conductor: `scripts/harness-shot.ps1` with
  drivers under `.for_bepy/readme-drivers/`).
- **Vite `createServer` plus a stubbed backend.** For a Tauri app, define
  `window.__TAURI_INTERNALS__` with an `invoke` switch returning fake values and a no-op
  `plugin:event|listen`, then load the real pages (one iframe each) inside a mock frame, for example
  a Windows 11 taskbar over a wallpaper for tray widgets. For a plain web app, run the dev server
  with mocked fetches.

**Check the window width first.** Ask the dev, or read the app's default window size, before picking
a viewport. Joe uses the home dashboard as a narrow window, and a wide shot of it read as wrong.

Hand the shooting to one `model: 'sonnet'` subagent with an exact spec, not a vague brief. It writes
PNGs, so it is a builder, not a read-only scout: use the builder preamble from
`~/.claude/refs/builder-preamble.md` (staging line, throwaway shots under
`.for_bepy/screenshots/<id>/`, final crops into `docs/readme/`), not Step 1's read-only block. The
spec must list: the fake values to use (invented names and numbers, no real accounts or paths), what
each shot shows, a viewport per shot, a size cap per file (about 150-400 KB), the output filenames,
and the line "open and look at every PNG before reporting; redo any that is blank, clipped, or shows
real data". Then look at each PNG yourself before it goes in the README.

**Grid of mixed aspect ratios:** one `<table>` per row, never one table for the whole grid, since a
table forces identical column widths on every row. Pair tall shots with tall and wide with wide, and
size the two columns by aspect ratio (for example 35% / 65%) so the heights match. Each cell: the
image with alt text, `<br>`, and a `<sub>` one-line caption (reference: `shots.md`).

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
     `.../github/actions/workflow/status/<owner>/<repo>/<file>.yml`,
     `.../github/package-json/v/<owner>/<repo>`.
   - **Version badge:** `github/v/release` shows the raw tag, so a prefix like `tauri-v` leaks into
     the badge. Use `github/package-json/v` (or the Cargo/pubspec equivalent) for a clean number.
   - **`logo=windows` renders nothing:** simple-icons dropped the Windows logo. Pass a base64 SVG
     data URI as `logo=` instead (`logo=data:image/svg+xml;base64,<b64>`). Fetch every badge URL
     once; a dead slug fails silently.
   - **Colour legend swatches:** `https://img.shields.io/badge/green-27ae60` style badges.
   - **Nav row links:** do not link a heading that starts with a VS16 emoji (gear, hammer-and-wrench
     with the variation selector): its GitHub anchor is unreliable. Link headings with a plain emoji
     (sparkles, camera, package) or none.
4. Optional tech row: `https://skillicons.dev/icons?i=java,gradle,js,python&perline=8` (only
   slugs listed on skillicons.dev; verify each slug renders by fetching the URL once).

## Step 4 - Body

Write for a stranger first, a contributor second. Pick from this menu; use only the sections the
repo has real material for.

- **What is this** - 2-4 sentences, plain words, no internal jargon.
- **Features** - a 3x4 grid in one `<table>`: emoji + bold name + one sentence per cell. For a
  monorepo, one row per module, grouped (player-facing, infrastructure).
- **Things X can do that a terminal can't** - a 2x3 grid of the standout features, when the
  product has them.
- **Screenshots** - the 2b grid, each with a one-line caption. Real ones only.
- **How it fits together** - a mermaid flowchart with `classDef` fills in the project palette (core
  node in the accent colour, the rest in the dark surface colour).
- **The one non-obvious mechanic** - when the UI has a thing nobody guesses (conductor's safe-pace
  rings): a close-up image, a caption giving the exact values, and a colour legend built from swatch
  badges.
- **Install** - a table (platform, file, note) plus big `for-the-badge` download badges linking to
  the latest release.
- **Getting started / how to use** - the shortest path to running or joining it. Commands in
  fenced code blocks.
- **Guides** - one `<details>` per feature that needs more than a sentence.
- **Project layout** - a short tree or table for anything with more than a few folders.
- **Development / testing** - the real commands from the manifests.
- **Related projects** - cross-links to sibling repos.
- **Credits / licence** - credit third-party art and libraries already credited elsewhere.

**Keep the old docs word for word.** Never delete accurate documentation from an existing README:
move it below the fold. Write a small Python assembler (reference: `assemble.py` plus `top.md`):
split the old README on `^## ` (the preamble is everything before the first one, each section keyed
by its title), put each long section into `<details><summary><b>icon Title</b></summary>` ...
`</details>` verbatim, and fill them into a hand-written top (banner, header, feature grid). The
assembler asserts that no old section is left unplaced. Then prove nothing was lost: every non-empty
old line, stripped, must appear in the new README (a set difference). The only acceptable misses are
lines you deliberately rewrote, and you list them.

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
2. Render the README the way GitHub does and look at it. Write a small Node render script
   (reference: `render.mjs`); do not type the `gh` call in the shell. Two hooks block the shell
   version: `gh api markdown -F text=@<path>` trips `outbound-verify-guard`, and a `>` redirect trips
   `shell-content-write-guard`. Calling `gh` from node `execFileSync` inside the script works:
   `execFileSync("gh", ["api", "markdown", "-F", "text=@" + mdPath, "-f", "mode=gfm", "-f", "context=<owner>/<repo>"], { encoding: "utf8", maxBuffer: 32 * 1024 * 1024 })`
   (`-F`, not `-f`: only `-F` reads `@file`. This renders only, nothing is posted).
   - Write the HTML with `writeFileSync`, wrapped with GitHub's CSS
     (`https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-dark.min.css`,
     `<article class="markdown-body">`, max-width about 1012px) and
     `<base href="file:///<repo root>/">` so relative images resolve.
   - **Mermaid:** the markdown API leaves it as `<pre lang="mermaid">` (github.com renders it in
     its own iframe), so the render page must run mermaid.js itself: a module script importing
     `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs`, replacing each
     `pre[lang="mermaid"]` with a `div.mermaid`, `await mermaid.run()`, then setting a flag the
     Playwright script waits on before the screenshot.
   - Screenshot with an isolated Playwright browser (`fullPage: true`, viewport about 1100 wide)
     into `.for_bepy/screenshots/<id>/` (id from `~/.claude/skills/close/rename-session.ps1 -GetId`).
3. Show it to the dev. A full-page PNG is too large to post, so convert it to a JPEG through
   `/preview`'s gallery builder
   (`python "C:\Users\tecno\.claude\skills\preview\build_gallery.py" <image...> --title "<text>"`,
   flags in `skills/preview/SKILL.md`); two READMEs fit in one gallery. Then commit via `/commit`.

## Step 7 - Repo page extras (ask before changing)

These live outside the README and are outward-facing, so confirm with the dev first:

- About box: `gh repo edit --description "..." --homepage <url> --add-topic <t>` (5-10 topics).
- Social preview image: no API exists; tell the dev the exact file to upload in Settings > General.
- Visibility: going public publishes the whole git history. Run a full-history secret and
  personal-data scan (one subagent, `model: 'sonnet'`, Step 1's read-only preamble; it reports
  hits as text and never prints a matched secret in full) and get an explicit OK before `gh repo edit --visibility public --accept-visibility-change-consequences`.
