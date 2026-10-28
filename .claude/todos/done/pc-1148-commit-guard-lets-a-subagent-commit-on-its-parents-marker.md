<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=9, reconfirm-count=1, content-hash=32a0fea6 -->
<!-- duplicate-checked: 2026-10-08; 1146 is the read-only staging-line wording (git add), not commit-guard allowing a subagent's git commit -->
# commit-guard lets a dispatched subagent commit on its parent session's marker

**Type:** skill-improvement
**Origin:** ai

## Goal
A dispatched subagent's raw `git commit` is denied unless it is a sanctioned committing builder
(`/mega-todos`), so a builder or reviewer can never land a commit on its own.

## Context
2026-10-08, ~/.claude loop-todos final review: a `READ-ONLY DISPATCH` reviewer's scratch-repo setup
failed (a `>` redirect was refused by shell-content-write-guard, so `git init` never ran), and its
next call, `git add -A && git commit -q -m seed`, ran against the real ~/.claude repo. It landed
`a9b2367 "seed"`, sweeping in two peer-filed todos, a dropped-findings.log line and an impeccable
cache file. `hooks/commit-guard.py` allowed it: subagents run under the parent's `session_id`, and
the parent had already written its `hooks/.session-markers/<session>` marker for its own `/commit`
calls, so the guard's marker check passed. CLAUDE.md says "subagents NEVER commit, except
/mega-todos agents".

## Approach
In `hooks/commit-guard.py` `main()`, deny a commit-landing invocation whose payload carries
`agent_id` (reuse `agent-todo-write-guard.py`'s `is_agent_call`, as `hooks/_testing_floor_lib.py`
already does), unless the sanctioned `/mega-todos` path applies: read
`skills/mega-todos/SKILL.md`'s commit block first to see what signal its builders carry (a per-commit
`.commit-marker-*` file, per commit-guard.py's own docstring) and keep that path working. Live guard:
one complete edit, run `python hooks/test_commit_guard.py` right after; add a case for an agent
payload with only the session marker (denied) and one for the `/mega-todos` path (allowed).

## Acceptance
- A payload with `agent_id` and only the parent's session marker is denied for `git commit`.
- A `/mega-todos` builder's sanctioned commit still passes.
- `python hooks/test_commit_guard.py` passes.

## Notes

- Done 2026-10-08: commit-guard computes is_agent_call (lazy-loaded from agent-todo-write-guard.py, as _testing_floor_lib.py does) and never lets a payload carrying agent_id ride the parent session marker; the /mega-todos per-commit .commit-marker-<guid> path (skills/mega-todos/SKILL.md:396-400) still passes. Tests: agent + parent marker denied, agent + fresh per-commit marker allowed and consumed, main session + its marker allowed.
