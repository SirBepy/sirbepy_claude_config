---
name: favicon
description: Triggers on /favicon only.
---

# /favicon

> Check for and generate favicon files (svg, png, ico) for any project type.

## Scripts

Both scripts live in the same folder as this SKILL.md.

- `svg-to-png.js` - converts SVG to PNG. Usage: `node <path-to-skill>/svg-to-png.js <input.svg> <output.png> <size>`
- `png-to-ico.js` - converts PNG to ICO. Usage: `node <path-to-skill>/png-to-ico.js <input.png> <output.ico>`

`png-to-ico.js` requires the `png-to-ico` npm package. **Before running it, always check and install if missing:**

```
npm list -g png-to-ico
```

If not found:

```
npm install -g png-to-ico
```

Do this every time, without asking the user.

## Flags

- `skipVerification` - skip early-out checks and regenerate everything from scratch

## Step 0 - Detect platform

Use these signals (first match wins):

- `src-tauri/` folder, `tauri.conf.json`, or `Cargo.toml` depending on `tauri` → `tauri`
- `next.config.*` or `next` in `package.json` deps → `next`
- `vite.config.*` + React deps in `package.json` → `react`
- `vite.config.*` without React → `vite`
- Plain `index.html` + no bundler config → `html`

Read the matching platform spec from this skill's `platforms/` folder (e.g. `platforms/tauri.md`). The spec defines:
- Canonical paths for SVG, PNG, ICO
- Which HTML file to update (or whether to skip)
- Any platform-specific extras

If no spec exists for the detected type, fall back to `platforms/html.md`.

## Step 1 - Detect what exists

Search the entire project for:

- `favicon.svg`
- `favicon.png`
- `favicon.ico`

Note current locations vs. canonical locations from the platform spec.

## Step 2 - Move to canonical locations if needed

Move any misplaced favicon files to their canonical paths per the platform spec. Update references in the HTML entry point after moving.

## Step 3 - Decide what to generate

### SVG exists

- Generate PNG from SVG if missing (use canonical PNG path from spec):

```
node <path-to-skill>/svg-to-png.js <svg-path> <png-path> 256
```

- Generate ICO from PNG if missing (use canonical ICO path from spec):

```
node <path-to-skill>/png-to-ico.js <png-path> <ico-path>
```

- If both already exist and `skipVerification` was not passed, tell the user and stop.

### PNG and ICO both exist, no SVG

- Warn: "favicon.svg is missing - SVG is recommended as the source of truth."
- Stop. Do NOT overwrite existing PNG or ICO. Do NOT design a new icon from scratch.

### Only PNG exists

- Generate ICO from PNG if missing.
- Warn: "favicon.svg is missing - SVG is recommended as the source of truth."

### Only ICO exists

- Print: "Only favicon.ico found. Generating new SVG + PNG + ICO from scratch."
- Follow the generation flow below.

### Nothing exists

- Print: "No favicon files found. Generating all 3 from scratch."
- Follow the generation flow below.

## Generation flow - designing a new icon from scratch

1. Read the project to understand its name, purpose, and vibe. Check `.portfolio-data/PORTFOLIO.md` and `README.md` if they exist.
2. Design a simple, bold SVG icon that fits the project - solid shapes, minimal detail, looks good at 32px.
3. Write it to the canonical SVG path from the platform spec.
4. Generate PNG, then ICO using the scripts above.

## Step 4 - Update HTML (platform-dependent)

Follow the platform spec for what HTML changes to make. Some platforms (e.g. Next.js App Router) need no link tags - the spec will say so.

## Step 5 - Platform extras

Run any platform-specific extras defined in the spec (e.g. Tauri native icon generation).

## Step 6 - Confirm

Tell the user what was found, what was generated, and what is still missing. Do not commit.
