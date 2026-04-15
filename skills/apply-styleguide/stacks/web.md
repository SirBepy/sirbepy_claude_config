# apply-styleguide - web stack

Assumes `common.md` is already loaded. This file only adds web-specific steps.

## 1. Ensure styleguide is linked

Check `index.html` for a `<link>` tag pointing to the styleguide CDN URL (see common.md). If missing, add it inside `<head>` before any other stylesheets:

```html
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css"
/>
```

## 2. Read the project CSS

Read all CSS files in `src/styles/`. Understand the current visual structure - layout, spacing, components, colors.

## 3. Apply token replacements

Go through all CSS files and apply the token replacement table from `common.md`.

## 4. Apply standard components in CSS

Replace custom implementations of card/button/badge/input patterns with the standard classes listed in `common.md`.

## 5. Apply classes to HTML

Open `index.html` and any other HTML files. Add appropriate classes to elements:

- Container/panel elements that are card-like -> `.card` or `.card-alt`
- `<button>` elements -> `.btn` + variant
- Badge/tag/pill elements -> `.badge` + variant
- `<input>`, `<select>`, `<textarea>` -> `.input`

## 6. Confirm

Follow the "Finish" section in `common.md`.
