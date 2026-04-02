---
name: favicon
description: Triggers on /favicon only.
---

# /favicon

> Check for and generate favicon files (svg, png, ico) in assets/images/.

## Scripts

- `svg-to-png.js` - converts SVG to PNG. Usage: `node svg-to-png.js <input.svg> <output.png> <size>`
- `png-to-ico.js` - converts PNG to ICO. Usage: `node png-to-ico.js <input.png> <output.ico>`

Both scripts live in the same folder as this SKILL.md.

## Flags

- `skipVerification` - if passed, skip early-out checks and regenerate everything from scratch (re-derive PNG from SVG, re-derive ICO from PNG, etc.)

## Step 1 - Detect what exists

Search the entire project for any of these files:

- `favicon.svg`
- `favicon.png`
- `favicon.ico`

The canonical location for svg and png is `assets/images/`. The canonical location for ico is the project root. If any are found elsewhere, note their current location.

## Step 2 - Move to canonical locations if needed

If any favicon files are found outside their canonical location, move them:

- `favicon.svg` and `favicon.png` → `assets/images/`
- `favicon.ico` → project root

Update references in `index.html` after moving.

## Step 3 - Decide what to generate

### SVG exists

- Generate `assets/images/favicon.png` from SVG if missing:

```
  node svg-to-png.js assets/images/favicon.svg assets/images/favicon.png 256
```

- Generate `favicon.ico` from PNG if missing:

```
  node png-to-ico.js assets/images/favicon.png favicon.ico
```

- If both already exist and `skipVerification` was not passed, tell the user and stop.

### Only PNG exists

- Generate `favicon.ico` from PNG if missing:

```
  node png-to-ico.js assets/images/favicon.png favicon.ico
```

- Warn the user: "favicon.svg is missing - ICO and PNG exist but SVG was not found. SVG is recommended as the source of truth."

### Only ICO exists

- Print: "Only favicon.ico found. Generating new SVG + PNG + ICO from scratch."
- Follow the generation flow below.

### Nothing exists

- Print: "No favicon files found. Generating all 3 from scratch."
- Follow the generation flow below.

## Generation flow - designing a new icon from scratch

1. Read the project to understand its name, purpose, and vibe. Check `.portfolio-data/PORTFOLIO.md` and `README.md` if they exist.
2. Design a simple, bold SVG icon that fits the project - solid shapes, minimal detail, looks good at 32px.
3. Write it to `assets/images/favicon.svg`.
4. Generate PNG:

```
   node svg-to-png.js assets/images/favicon.svg assets/images/favicon.png 256
```

5. Generate ICO:

```
   node png-to-ico.js assets/images/favicon.png favicon.ico
```

## Step 4 - Update index.html

Ensure these tags exist inside `<head>`. Add any that are missing:

```html
<link rel="icon" type="image/x-icon" href="favicon.ico" />
<link rel="icon" type="image/png" href="assets/images/favicon.png" />
<link rel="icon" type="image/svg+xml" href="assets/images/favicon.svg" />
```

## Step 5 - Confirm

Tell the user what was found, what was generated, and what is still missing.
Do not commit - the user handles that.
