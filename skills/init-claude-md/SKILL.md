---
name: init-claude-md
description: Triggers on /init-claude-md only.
---

# /init-claude-md

> Generate or update the project-level CLAUDE.md file.

## Workflow

### Step 0 - Check if already done

If the user passed `skipVerification`, skip this step entirely and proceed to Step 1.

If `CLAUDE.md` exists and already has the correct structure (Project section with Type and Deploy, Structure section, Rules section), print:

```
/init-claude-md - already complete, skipping.
```

And stop. Only proceed if CLAUDE.md is missing or malformed.

### Step 1 - Check if CLAUDE.md exists

If it exists, read it. The goal is to update it to match the standard structure below while preserving anything that looks intentional and project-specific.

If it does not exist, create it from scratch.

### Step 2 - Explore the project

Read enough to confidently fill the standard fields:

- Check for `package.json`, `vite.config.*`, `index.html`, `pubspec.yaml`, `default.project.json` or equivalent to determine project type
- Check for `.github/workflows/` to determine deploy setup
- Check for `.prettierrc`, `.gitignore` to see what boilerplate exists
- Check folder structure to determine the source layout

Do not read every file. Just enough to answer: what type is this, how is it structured, how does it deploy.

### Step 3 - Write CLAUDE.md

Write or update the file at the project root. Follow this structure exactly:

```markdown
## Project

Type: html | vite | react | roblox | flutter | other
Deploy: github-pages | none | other

## Structure

Brief one-liner of the source layout, e.g. "src/styles.css, src/script.js, assets/images/, assets/fonts/, assets/data/"

## Rules

- [any project-specific rules that are genuinely useful]
```

### Type reference

| Value     | When to use                      |
| --------- | -------------------------------- |
| `html`    | Plain HTML/CSS/JS, no build step |
| `vite`    | Vite project, no framework       |
| `react`   | React project (Vite or CRA)      |
| `roblox`  | Roblox Luau project              |
| `flutter` | Flutter/Dart project             |
| `other`   | Anything else                    |

### Rules section guidelines

Only add rules that are genuinely project-specific and that Claude would not know without being told. Good examples:

- "No build step, no npm"
- "CSS vars from settings widget, never hardcode colors"
- "MUST have favicon.svg + favicon.png + favicon.ico in assets/images/"
- "Auto-commit: yes"

Do not add rules that are already in the global CLAUDE.md or that are obvious from the project type.

Keep the file under 30 lines total. Every line must earn its place.

### Step 4 - Confirm

Tell the user what was written or updated and flag any assumptions made.
Do not commit - the user handles that.
