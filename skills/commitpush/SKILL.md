---
name: commitpush
description: Commit then immediately push. Triggers on /commitpush, /commitpush v, and /commitpush bump.
---

# Commitpush Skill

## `/commitpush` Command

Run the full commit flow then push:

1. Run `git status`
2. Run `git diff` to understand the changes
3. Infer the right commit prefix (FEAT, FIX, REFACTOR, CHORE, DOCS, TEST, STYLE, DATA)
4. Check if a linter exists - if yes, run it and fix all issues first
5. Stage all relevant files by name (`git add <file>` - never `-A`)
6. Commit with a message following the style rules below
7. Run `git push`

If there is nothing to commit, say so and stop. Do not push if the commit failed.

## `/commitpush v` / `/commitpush bump` Command

Same as `/commitpush` but also bumps the patch version in `package.json` (e.g. 1.0.0 -> 1.0.1):

1. Check if `package.json` exists in the repo root
2. If yes, read the current version, increment the patch number, write it back
3. Stage `package.json` along with the other changed files
4. Include the version bump in the same commit - do not make a separate commit for it
5. Mention the new version in the commit message, e.g. `CHORE: bump to v1.0.1 + <summary of changes>`
6. Run `git push`

If no `package.json` exists, skip the version step and commit+push normally.

## Commit Prefixes

- `FEAT:` - new feature
- `FIX:` - bug fix
- `REFACTOR:` - code restructure, no behavior change
- `CHORE:` - maintenance, config, tooling
- `DOCS:` - readme, comments, documentation
- `TEST:` - adding or updating tests
- `STYLE:` - formatting only, no logic change
- `DATA:` - hardcoded data, content, or copy changes

## Commit Message Style

- One purpose per commit. Many files is fine as long as it's one logical change.
- Message should make it clear exactly what was done, just from the title.
- No body needed unless something genuinely needs explanation.
- Never add `Co-authored-by: Claude` or any AI attribution. Commit as Joe only.

## Shell Rules

- Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
- Never use `cd` before git commands. Use `git -C /absolute/path <command>` for a specific directory.
