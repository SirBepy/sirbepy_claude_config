---
name: apply-styleguide
description: Triggers on /apply-styleguide only.
---

# /apply-styleguide

> Apply the bepy styleguide to the project - replace hardcoded values with CSS vars and apply standard components.

## Styleguide

Hosted at: `https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css`

## Step 1 - Ensure styleguide is linked

Check `index.html` for a `<link>` tag pointing to the styleguide CDN URL. If missing, add it inside `<head>` before any other stylesheets so project styles can override it:

```html
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css"
/>
```

## Step 2 - Read the project CSS

Read all CSS files in `src/styles/`. Understand the current visual structure - layout, spacing, components, colors.

## Step 3 - Replace hardcoded values

Go through all CSS files and replace:

| Hardcoded               | Replace with                                                                      |
| ----------------------- | --------------------------------------------------------------------------------- |
| Background colors       | `var(--color-background)` or `var(--color-surface)` or `var(--color-surface-alt)` |
| Text colors             | `var(--color-text)` or `var(--color-text-muted)`                                  |
| Accent/highlight colors | `var(--color-primary)` or `var(--color-secondary)`                                |
| Border colors           | `var(--color-border)`                                                             |
| Font families           | `var(--font-body)` or `var(--font-heading)` or `var(--font-mono)`                 |
| Border radius values    | `var(--radius-card)` or `var(--radius-badge)`                                     |
| Box shadows             | `var(--shadow-card)`                                                              |

Use judgment for ambiguous colors - pick the closest semantic match, not just the closest color value.

Remove any `background` or `background-color` rules from `body` or `html` - the animated background script handles this.

## Step 4 - Apply standard components to CSS

Replace any custom implementations of these patterns with the standard styleguide classes:

- Card-like containers → add `.card` or `.card-alt`
- Buttons → ensure `button` elements rely on styleguide base styles, add `.btn-primary`, `.btn-outline`, or `.btn-ghost` as appropriate
- Badges/tags/pills → `.badge`, `.badge-tech`, `.badge-success`, `.badge-info`
- Text inputs, selects, textareas → `.input`

## Step 5 - Apply classes to HTML

Open `index.html` and any other HTML files. Add appropriate classes to elements:

- Container/panel elements that are card-like → add `.card` or `.card-alt`
- `<button>` elements → add `.btn` + the appropriate variant
- Badge/tag/pill elements → add `.badge` + appropriate variant
- `<input>`, `<select>`, `<textarea>` → add `.input`

Keep layout, spacing, and structural classes exactly as they are - only add styleguide classes, never remove existing ones.

## Step 6 - Confirm

Print a summary of:

- How many hardcoded values were replaced
- Which components were applied
- Anything that was ambiguous or skipped

Do not commit - the user handles that.
