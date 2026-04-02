---
name: bepy-project-setup
description: Triggers on /bepy-project-setup only.
---

# /bepy-project-setup

> Full project standardization flow - runs all bepy skills in order.

## Flags

- `auto` - Skip all prompts, run everything, auto-yes all questions (including PWA). No user interaction at all.

## Step 0 - Git init

Run `/git-init` before anything else.

## Step 1 - Ask what to skip

If `auto` flag is passed, skip nothing and proceed to Step 2.

Otherwise, first ask using AskUserQuestion:

- "Run everything"
- "Let me pick what to skip"

If the user picks "Run everything", skip nothing and proceed to Step 2.

If the user picks "Let me pick what to skip", use AskUserQuestion with multiSelect to ask:

"Which skills do you want to SKIP? (Everything else will run)"

Options:
- "/init-claude-md" - Generate or update CLAUDE.md
- "/migrate-structure" - Normalize file structure, add missing boilerplate
- "/readme" - Generate or update README.md
- "/portfolio-data" - Generate or update portfolio metadata
- "/favicon" - Check and generate favicon svg + png + ico
- "/meta-tags" - Add missing meta tags to index.html
- "/update-workflow" - Ensure deploy.yml matches the correct template
- "/inject-widgets" - Inject settings widget and animated background
- "/apply-styleguide" - Apply bepy styleguide and CSS vars

## Step 2 - Run skills in order

Run all non-skipped skills in the order listed. For each one:

- Print `Running /skill-name...` before starting
- Run the full skill as defined in its SKILL.md
- Print `Done /skill-name` when complete
- Move to the next one

Do not stop between skills unless a skill requires user input. Handle the input and continue.

## Step 3 - Suggest context compact

After `/portfolio-data` and `/favicon` are done, print:

```
Heavy context steps done. Consider running /compact before continuing if context feels large.
```

Then continue automatically unless the user says to pause.

## Step 4 - Ask about PWA

If `auto` flag is passed, run `/pwa` without asking.

Otherwise, ask using AskUserQuestion:

- "Set this up as a PWA (adds manifest.json + service worker)"
- "Skip PWA for now"

If yes, run `/pwa`.

## Step 5 - Commit

After everything is done (including PWA if selected), run `/commit` with the message:

```
MAJOR: bepy project setup
```

## Step 6 - GitHub Pages (web projects only)

Run `/github-pages-init`. It will skip automatically if not a web project.

## Step 7 - Summary

Print a summary of everything that ran:

```
Done. Here's what ran:

/init-claude-md     - created
/migrate-structure  - moved script.js to src/scripts/, added .prettierrc
/readme             - generated
/portfolio-data     - updated, screenshots taken
/favicon            - generated svg + png + ico
/meta-tags          - added og:title, og:description, og:image
/update-workflow    - already up to date, skipped
/inject-widgets     - injected both scripts
/apply-styleguide   - replaced 14 hardcoded values, applied .card to 3 elements

Don't forget to review and commit when ready.
```

## Notes

- Auto-commit at the end via /commit.
- If a skill is skipped by user, note it as "skipped by user" in the summary.
- If a skill has nothing to do, note it as "skipped - nothing to do" in the summary.
