---
name: init-claude-md
description: Triggers on /init-claude-md only.
---

# /init-claude-md

> Generate or update the project-level CLAUDE.md file.
>
> **Reader:** Claude Code, not a human. Optimize for Claude's effectiveness, not human brevity. Include anything that takes multiple files to discover. Omit only what Claude can trivially find in one read (e.g. a single config file).

## Workflow

### Step 0 - Check if already done

If the user passed `skipVerification`, skip this step entirely and proceed to Step 1.

If `CLAUDE.md` exists and already has the correct structure (Project section with description + Type + Deploy, Structure section, Commands section, Rules section - Architecture section optional), print:

```
/init-claude-md - already complete, skipping.
```

And stop. Only proceed if CLAUDE.md is missing or malformed.

### Step 1 - Check if CLAUDE.md exists

If it exists, read it. The goal is to update it to match the standard structure below while preserving anything that looks intentional and project-specific.

If it does not exist, create it from scratch.

### Step 2 - Explore the project

Read enough to confidently fill the standard fields and understand the architecture:

- Check for `package.json`, `vite.config.*`, `index.html`, `pubspec.yaml`, `default.project.json` or equivalent to determine project type
- Check for `.github/workflows/` to determine deploy setup
- Check for `.prettierrc`, `.gitignore` to see what boilerplate exists
- Check folder structure to determine the source layout
- Read `package.json` scripts section to find dev/build/test commands
- For non-trivial projects: read key entry points and module boundaries to map the subsystem architecture

Do not read every file. Answer: what type is this, how is it structured, how does it deploy, how do you verify changes, and what are the subsystems a new Claude session would need a map to navigate.

### Step 3 - Write CLAUDE.md

Write or update the file at the project root. Follow this structure exactly:

```markdown
## Project

One sentence: what this app does and who it's for.

Type: html | vite | react | roblox | flutter | other
Deploy: github-pages | none | other

## Structure

Brief one-liner of the source layout, e.g. "src/styles.css, src/script.js, assets/images/, assets/fonts/, assets/data/"

## Commands

- Dev: `<dev command>`
- Verify: `<build or type-check command>`
- [only include if project has a test command] Test: `<test command>`

## Architecture

[For simple projects: omit this section entirely.]

[For projects with multiple subsystems, non-obvious module boundaries, or cross-cutting flows: describe them here. Include file maps, data flow, and anything that takes more than one file to understand. This is the highest-value section for Claude - a session without this map re-discovers the architecture every time.]

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
- Non-obvious constraints that would cause mistakes if unknown (e.g. "new settings field requires updating both schema.ts AND settings.rs")

Do not add rules that are already in the global CLAUDE.md or that are obvious from the project type.

No line limit. Every line must earn its place by this test: "would Claude need to open a file to know this?" If yes, include it. If no, omit it. Do not repeat what is already in the global CLAUDE.md or obvious from file names and project type.

### Step 4 - Confirm

Tell the user what was written or updated and flag any assumptions made.
Do not commit - the user handles that.
