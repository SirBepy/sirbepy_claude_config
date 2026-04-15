# apply-styleguide - common rules

Shared across every stack. The stack-specific file (`stacks/<stack>.md`) handles how these rules apply in that environment.

## Styleguide source

Hosted at: `https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/styleguide.css`

Every rendered HTML surface (web page or embedded webview) must load this file via `<link rel="stylesheet">` in `<head>` before any project stylesheet, so project styles can override it.

## Token replacements

Replace hardcoded values with CSS vars:

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

## Standard components

Replace custom implementations with standard styleguide classes wherever they apply:

- Card-like containers -> `.card` or `.card-alt`
- Buttons -> `.btn` base + `.btn-primary`, `.btn-outline`, or `.btn-ghost`
- Badges/tags/pills -> `.badge`, `.badge-tech`, `.badge-success`, `.badge-info`
- Text inputs, selects, textareas -> `.input`

Keep existing layout, spacing, and structural classes - only add styleguide classes, never remove.

## Finish

- Print a summary of what was changed, what was applied, and anything ambiguous or skipped.
- Do not commit - the user handles that.
