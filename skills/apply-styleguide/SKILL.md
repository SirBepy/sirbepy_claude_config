---
name: apply-styleguide
description: Triggers on /apply-styleguide only.
---

# /apply-styleguide

> Apply the bepy styleguide to the project - replace hardcoded values with CSS vars and apply standard components.

## How this skill is structured

- `common.md` - rules shared by every stack (CDN URL, token table, component classes, finish rules).
- `stacks/<stack>.md` - stack-specific steps that assume `common.md` is already loaded.

Adding a new stack = add one file under `stacks/` and one row to the dispatch table below. Do not inline stack logic in this file.

## Dispatch

1. Detect the project stack from files at the repo root:

    | Signal                                                                            | Stack    | File to load       |
    | --------------------------------------------------------------------------------- | -------- | ------------------ |
    | `index.html` exists                                                               | `web`    | `stacks/web.md`    |
    | `pyproject.toml` exists AND (tkinter/pywebview/Qt imports OR `src/<pkg>/` layout) | `python` | `stacks/python.md` |

2. Read `common.md` first, then the matching stack file. Follow both.

3. If no row matches, print that the styleguide does not apply to this project type and stop. Do not guess.
