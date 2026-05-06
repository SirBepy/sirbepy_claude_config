---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, pushbump, pushnbump) to commit changes.
argument-hint: "[v|bump|push|pushbump|pushnbump|onlyv|onlybump]"
---

# /commit

> Commit changes into clean, well-organized commits.

## `/commit`

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.). Only read it once per session.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
6. Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait for the result. If it fails, **abort the commit**, print the failing output, and explain to the user exactly why the commit was aborted (which command failed, what it printed, and that they need to fix it or tell you to skip). Do not stage or commit anything until the user either fixes it or explicitly says to skip.
7. Stage all relevant files by name
8. Commit

If nothing to commit, say so and stop.

## `/commit v` / `/commit bump`

Same as `/commit` but also bumps the patch version before committing (e.g. 1.0.0 -> 1.0.1).

Version bump procedure:
1. Find `package.json` in the repo root. If it exists, it is the **source of truth** - read the version from it, increment the patch number, and write it back.
2. Find any other `.json` files in the repo root that contain a top-level `"version"` field (e.g. `tauri.conf.json`, `manifest.json`). Update each one to match the new version.
3. Stage all modified version files alongside the other changed files.

Commit message follows the normal style - no need to mention the version bump.

If no `package.json` exists, skip the version step and commit normally.

## `/commit push`

Same as `/commit` but also runs `git push` after committing.

Do not push if the commit failed or there was nothing to commit.

## `/commit pushbump`

Same as `/commit v` but also runs `git push` after committing.

Do not push if the commit failed or there was nothing to commit.

## `/commit pushnbump`

Commits changes and version as **two separate commits**, then pushes.

Order:
1. Do the normal commit for changed files (same as `/commit`).
2. Bump the patch version (same procedure as `/commit v`).
3. Stage only the version files.
4. Commit with message: `VERSION: <new-version>` — where `<new-version>` is the full version string after bumping. If a build number field (e.g. `"build"` in `package.json` or `tauri.conf.json`) exists alongside the version, append it: `VERSION: 1.0.1+21`.
5. Run `git push`.

Do not push if either commit failed or there was nothing to commit.

## `/commit onlyv` / `/commit onlybump`

Only bumps the patch version. No other changes staged.
Commit message is always: `CHORE: bump to v1.0.1` (with the actual new version).

Version bump procedure: same as `/commit v` above.

If no `package.json` exists, say so and stop.

## Prefixes

- `FEAT:` - new feature
- `FIX:` - bug fix
- `REFACTOR:` - code restructure, no behavior change
- `CHORE:` - maintenance, config, tooling
- `DOCS:` - readme, comments, documentation
- `TEST:` - adding or updating tests
- `STYLE:` - formatting only, no logic change
- `DATA:` - hardcoded data, content, or copy changes

## Rules

- Project `.claude/commit-style.md` overrides these rules when present.
- One purpose per commit. Many files is fine if it's one logical change.
- Prefer more commits over fewer big ones. Split unrelated changes.
- Message title alone should make clear what was done.
- No body unless something genuinely needs explanation.
- Never add `Co-authored-by: Claude` or any AI attribution.
- Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
- Never use `cd` before git commands. Use `git -C /absolute/path <command>`.
- Stage files by name. Never `git add -A`.

## Backdating commits

- When the user asks for a specific commit time, jitter it to look organic:
  - Always randomize the seconds (00-59).
  - Shift the minutes by a few (typically +/- 1-4) from whatever was requested.
  - Example: user says "27 minutes after the previous commit" → don't use exactly :45:00; use :43:17, :46:52, etc.
- Apply the same timestamp to both author and committer dates: `GIT_COMMITTER_DATE="..." git ... commit --date="..." ...`.
- Confirm the resulting timestamp back to the user after committing.
