---
name: bepy-project-setup
description: Triggers on /bepy-project-setup only.
---

# /bepy-project-setup

> Full project standardization flow - runs all bepy skills in order.

## Step 0 - Git init and .gitignore

Before anything else:

1. Check if a git repo exists (`git status`)
2. If not, run `git init`
3. Ensure `.gitignore` exists. If missing, create one with these defaults:
   ```
   .DS_Store
   node_modules/
   dist/
   .env
   ```
   If it already exists, check it includes `.DS_Store` - if not, add it at the top.
4. Check if there are any commits (`git log --oneline -1`)
5. If no commits exist, stage all current files by name and commit:
   `MAJOR: initial commit`
6. If commits already exist, skip this step

## Step 1 - Ask what to skip

Use AskUserQuestion with multiSelect to ask:

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

If the user selects nothing (or says "go" / "run all"), run everything.

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

After all skills are done, ask using AskUserQuestion:

- "Set this up as a PWA (adds manifest.json + service worker)"
- "Skip PWA for now"

If yes, run `/pwa`.

## Step 4.5 - Commit

After everything is done (including PWA if selected), run `/commit` to commit all changes.

## Step 5 - Summary

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
