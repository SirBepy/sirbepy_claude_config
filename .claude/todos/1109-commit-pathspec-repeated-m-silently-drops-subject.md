<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=9, reconfirm-count=1, content-hash=ba116bc7 -->
<!-- duplicate-checked: sibling of done/1053 (the same overwrite-on-repeat bug, for --force); this is the -m flag, still open -->
# commit-pathspec.sh silently drops every -m but the last

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/commit-pathspec.sh` must either support repeated `-m` (subject + body paragraphs,
the way `git commit -m A -m B` does) or refuse a second `-m` loudly. Today it does neither.

## Context

Found 2026-10-06 in the claude_usage_in_taskbar mobile-polish session. The call was
`commit-pathspec.sh ... -m "FEAT: <subject>" -m "<body paragraph>" -- <files>`. The commit landed
with the BODY paragraph as its subject line and the real subject gone. Every check passed and the
script printed `[commit] committed`, so nothing flagged it; it was only caught by reading
`git log` afterwards, then repaired with a same-tree `commit-tree` + `update-ref` rewrite.

Cause, read this session: the argument loop at `skills/commit/commit-pathspec.sh:88` is
`-m|--message) message="${2:-}"; shift 2 ;;` - each `-m` overwrites `message`. Todo 1053 (done)
fixed exactly this shape for `--force` one line above; `-m` was left as is.

`/commit`'s SKILL.md documents the script as taking `-m "<message>"` and never says a body needs
a different form, so passing `-m` twice is the natural git habit.

## Approach

Collect every `-m` into an array and pass each through as its own `-m` to the final
`git commit` (git joins them with a blank line). Add assertions to
`skills/commit/test_commit_pathspec.sh` (where 1053's tests live) for a two-`-m` call.

## Acceptance

- `commit-pathspec.sh -m A -m B -- f` produces a commit whose `%s` is `A` and body is `B`.
- A single `-m` still works unchanged.
- `python ci/run_all.py` is green.
