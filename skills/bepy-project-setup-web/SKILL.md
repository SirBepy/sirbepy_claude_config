---
name: bepy-project-setup-web
description: Web/HTML project standardization flow - runs favicon, meta-tags, PWA, GitHub Pages, styleguide, deploy workflow, etc. For Roblox/Luau projects use /bepy-project-setup-roblox instead.
disable-model-invocation: true
---

# /bepy-project-setup-web

> Full web project standardization flow - runs all bepy web skills in order.

## Flags

- `pick` (or free text like "let me pick" / "ask me what to skip") - opt into the interactive
  picker instead of the default run-everything behavior.

## Step 0 - Git init

Before anything else:

1. If not already a git repo (`git status`), run `git init` with `main` as the
   initial branch.
2. If `.gitignore` is missing, create one with `.DS_Store`, `node_modules/`,
   `dist/`, `.env`.
3. If there are no commits yet and files exist to stage, run `/commit` with a
   `CHORE:` prefix for the initial commit.

## Step 1 - Determine what to skip

Run everything by default, no prompt - proceed straight to Step 2, unless the dev's invocation
text does one of these:

- Names specific step(s) to skip (e.g. "skip favicon and readme") - skip only those, run
  everything else, proceed to Step 2.
- Explicitly asks to pick/choose/be asked (`pick` flag, "let me pick", "ask me what to skip") -
  fall back to the interactive picker below. This is the escape hatch for a project where a step
  genuinely must not run unattended (e.g. `/update-workflow` would overwrite a hand-tuned
  deploy.yml the dev doesn't want templated).

**Interactive picker** (only when explicitly requested): use AskUserQuestion with multiSelect to
ask:

"Which skills do you want to SKIP? (Everything else will run)"

Options:
- "/init-claude-md" - Generate or update CLAUDE.md
- "/readme" - Generate or update README.md
- "/favicon" - Check and generate favicon svg + png + ico
- "/meta-tags" - Add missing meta tags to index.html
- "/update-workflow" - Ensure deploy.yml matches the correct template
- "/inject-widgets" - Inject settings widget and animated background
- "/apply-styleguide" - Apply bepy styleguide and CSS vars
- "/portfolio-data" - Generate or update portfolio metadata (runs after styleguide so screenshots reflect final look)

## Step 2 - Run skills in order

Run all non-skipped skills in the order listed. For each one:

- Print `Running /skill-name...` before starting
- Run the full skill as defined in its SKILL.md
- Print `Done /skill-name` when complete
- Move to the next one

Do not stop between skills unless a skill requires user input. Handle the input and continue.

## Step 3 - PWA setup

Run `/pwa` by default. Skip only if the dev's invocation text says not to (e.g. "skip pwa", "no
pwa", "without PWA"), or the `pick` escape hatch from Step 1 was used and PWA was picked to skip.

## Step 4 - Commit

After everything is done (including PWA if selected), run `/commit`:

```
CHORE: bepy project setup
```

## Step 5 - GitHub Pages (web projects only)

Run `/github-pages-init`. It will skip automatically if not a web project.

## Step 6 - Summary

Print a summary of everything that ran:

```
Done. Here's what ran:

/init-claude-md     - created
/readme             - generated
/favicon            - generated svg + png + ico
/meta-tags          - added og:title, og:description, og:image
/update-workflow    - already up to date, skipped
/inject-widgets     - injected both scripts
/apply-styleguide   - replaced 14 hardcoded values, applied .card to 3 elements
/portfolio-data     - updated, screenshots taken
```

## Notes

- Auto-commit at the end via /commit.
- If a skill is skipped by request (named skip or interactive picker), note it as "skipped by request" in the summary.
- If a skill has nothing to do, note it as "skipped - nothing to do" in the summary.
