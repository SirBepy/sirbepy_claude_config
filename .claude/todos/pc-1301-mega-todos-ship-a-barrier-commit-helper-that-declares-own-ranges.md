<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: archive-batch.ps1 covers the archive half only; this is the per-todo code commit half -->
# /mega-todos: ship a barrier-commit helper that declares own ranges and never swallows a refusal

**Type:** skill-improvement
**Origin:** ai
**Summary:** In `barrier` COMMIT_MODE the main thread hand-rolled the same commit step about 30 times in one run (a scratch wrapper around `hunk-ranges.sh` plus `commit-pathspec.sh`, a CRLF-safe pathspec parser for the archive commit), so the skill should ship that helper like it ships `archive-batch.ps1`.

## Goal
`skills/mega-todos/` has a script that takes a title, a body and a file list, declares each file's current hunk ranges as own, runs `commit-pathspec.sh`, and exits with that script's own status, so a barrier commit is one call and a refused commit can never read as success.

## Context
Run of 2026-11-03 (45 commits). `commit-pathspec.sh` refused every commit with "UNVERIFIED, refusing (3 live session markers)" because builder subagents leave session markers, so each call needed `--own-range` per file; `skills/commit/hunk-ranges.sh` (pc-1247) prints exactly those flags. The first attempt chained commits with `| tail` and `&&`: a coverage refusal (a comment-only change needs `--force coverage-tests`) was swallowed and the chain carried on until the new pipe guard (pc-1223) caught the shape. The wrapper also needed `tr -d '\r'` on the pathspec read from `archive-batch.ps1` output (Python on Windows writes CRLF, which made every path read as "not on disk"), and an optional `FORCE` env for `coverage-tests` on doc-only or hyphen-named test files.

## Approach
Add `skills/mega-todos/barrier-commit.sh` with a `--force` pass-through and a test, and have `SKILL.md`'s "Barrier COMMIT_MODE" call it. Teach `archive-batch.ps1` to also write its pathspec to a file the helper can read with no CRLF. Do not edit `SKILL.md` from inside a running /mega-todos.

## Acceptance
- [ ] One call commits a todo's files by pathspec and exits non-zero on any refusal.
- [ ] The archive commit takes the pathspec from `archive-batch.ps1` without hand parsing.
- [ ] A test covers a refused commit not reading as success.
