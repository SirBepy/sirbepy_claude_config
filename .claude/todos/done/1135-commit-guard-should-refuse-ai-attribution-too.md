<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; done/1117 covers commit-pathspec.sh only, and named this hook as its optional, undone step 2 -->
# commit-guard.py lets a raw `git commit -m` carry a Co-Authored-By: Claude trailer

**Type:** task
**Origin:** ai

## Goal
The by-hand `git commit -m` fallback refuses AI attribution the same way `commit-pathspec.sh` does.

## Context
Todo 1117 (2026-10-08, loop-todos cycle 2) made `skills/commit/commit-pathspec.sh` refuse a message
with a line matching `^co-authored-by:.*(claude|anthropic)` or containing
`generated with \[?claude code` (case-insensitive). Its optional step 2, the same check in
`hooks/commit-guard.py` for a raw `git commit -m`, was left out of that builder's lane.
`/commit`'s Rules still say "Never add `Co-authored-by: Claude` or any AI attribution", and the
harness injects a reminder every session that asks for exactly that trailer.

## Approach
Read how `hooks/commit-guard.py` parses the command first. Deny a `git commit` whose `-m`/`--message`
values match either pattern, with a reason naming the matched line. Reuse the same two patterns
(ideally from one shared place). Live guard: write it in one complete edit and run
`python hooks/test_commit_guard.py` right after; add a refused trailer case, an allowed human
Co-Authored-By, and an allowed "Player Claude" subject.

## Acceptance
- `git commit -m "X" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` is denied by the hook.
- `git commit -m "FIX: Player Claude listener"` is allowed.
- `python hooks/test_commit_guard.py` passes.

## Notes

- commit-guard.py denies a git commit / commit-tree whose -m, -mX, --message or --message= value has a line matching commit-pathspec.sh's two AI-attribution patterns, checked before the bypass env var; 5 cases RED then GREEN in hooks/test_commit_guard.py. A first edit missed 'import re' for under a minute, during which the guard failed open (module-level NameError), fixed and re-tested.
