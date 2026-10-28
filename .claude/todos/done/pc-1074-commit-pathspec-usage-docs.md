<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=4e465905 -->
<!-- duplicate-checked: surfaced from mc_plugins_tag session 2026-10-02/03 -->
# commit/SKILL.md documents commit-pathspec.sh without its required flags

**Type:** skill-improvement
**Origin:** ai

## Goal
Following `skills/commit/SKILL.md` step 8 verbatim produces a working `commit-pathspec.sh` call on the first try.

## Context
In the mc_plugins_tag session (2026-10-02/03) the first several commits each failed once: SKILL.md shows `bash commit-pathspec.sh -m "<message>" -- <files>`, but the script refuses with "--expect-branch, --expect-sha, -m and -- <files> are all required". `--force` repeated twice silently honoured only one (it takes a comma list, documented only in the script header), and passing a directory (`server`) as a pathspec made foreign-hunk and coverage checks misfire ("foreign-hunks-inside-your-hunk 1-325", coverage REFUSED for files inside it).

## Approach
In `skills/commit/SKILL.md` step 8's scripted-chain paragraph, show the full invocation `bash ~/.claude/skills/commit/commit-pathspec.sh --expect-branch <branch> --expect-sha $(git rev-parse HEAD) -m "<msg>" -- <file> <file>`, state `--force a,b` comma syntax, and say pathspecs must be individual files (or make the script expand directories itself).

## Acceptance
- A fresh session following SKILL.md commits without a usage error on the first call.

## Notes

- Duplicate of 1004 - merged during /cleanup-todos 2026-10-05; nothing unique to salvage.
