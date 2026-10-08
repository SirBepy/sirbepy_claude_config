<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
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
