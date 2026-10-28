<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=ecb0429b -->
<!-- duplicate-checked: 2026-10-06; grepped commit-pathspec.sh and the backlog for "--todo" and todo-archive pathspec handling, no hits. -->
# commit-pathspec.sh should take a todo id and add that todo's archive paths itself

**Type:** skill-improvement
**Origin:** ai

## Goal
A lane commit that closes a todo names the todo id once (`--todo 1097`) and `commit-pathspec.sh`
adds the right backlog paths, instead of every caller hand-building them.

## Context
The 2026-10-06 /loop-todos run (cycles 2-3) committed about 20 lanes. Each one closed a todo with
`skills/close/complete-todo.ps1`, which moves `.claude/todos/<id>-*.md` to `.claude/todos/done/`. The
commit then has to name BOTH halves: the new `done/<id>-*.md` (untracked) and, only when the source
was tracked, the deleted `.claude/todos/<id>-*.md` (a peer-filed todo is often untracked, so there is
no deletion to name). Getting this wrong is the half-committed-move case the coverage check in
`skills/commit/commit-pathspec.sh` exists to catch. The run worked around it with a throwaway
wrapper script that globbed `done/<id>-*.md` and ran `git ls-files ".claude/todos/<id>-*.md"`
per id before calling commit-pathspec.sh; that wrapper was rebuilt in-session and deleted after.

## Approach
Add a repeatable `--todo <id>` flag to `skills/commit/commit-pathspec.sh`: for each id, append
`.claude/todos/done/<id>-*.md` if it exists and `.claude/todos/<id>-*.md` if `git ls-files` still
tracks it, relative to the repo root, before classification. Document it in `skills/commit/SKILL.md`
step 8 next to the script's other flags, and mention it in `skills/close/ai-todos-format.md` where
`complete-todo.ps1` is described. Add cases to `skills/commit/test_commit_pathspec.sh`: a tracked
todo archived (both paths land, no coverage refusal) and an untracked todo archived (only the done/
file lands).

## Acceptance
- `--todo <id>` commits a tracked todo's move whole and an untracked todo's done/ file alone.
- `bash skills/commit/test_commit_pathspec.sh` passes (give it timeout 600000).

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): commit-pathspec.sh --todo <id> (repeatable) adds the done/ copy and the tracked source deletion; documented in commit SKILL.md step 8 and ai-todos-format.md; r36/r37 tests.
