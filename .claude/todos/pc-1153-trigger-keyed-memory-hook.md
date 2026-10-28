<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits (16, 233, 243, 368, 487) only share the words file/skill/repo/touched; none is about injecting memory -->
# Trigger-keyed memory: inject a memory when its file, skill or repo is touched

**Type:** task
**Origin:** dev
**Summary:** A memory file can declare triggers and is injected into context the moment its file, skill or repo is touched, including into subagent dispatches.

## Why

Joe picked this design on 2026-10-08. Past misses: a Clockify run skipped the one memory file holding the meal-gap rule, and Joe had to restate an overlap rule for the third time.

## Goal

A memory file can declare `triggers:` (path globs, skill names, repo) and gets injected into
context at the moment one fires, including into subagent dispatches, instead of depending on
someone remembering to read it. `once: true` makes it prospective memory ("next time X is
touched, do Y").

## Context

Designed in `refs/permanent-memory.md` ("Trigger-keyed memory"), picked by Joe on 2026-10-08 in
todo 95's brainstorm. Evidence: done/1017 (a Clockify run skipped the one memory file holding the
meal-gap rule), done/448 (Joe restated an overlap rule for the 3rd time), done/53 (a subagent hit a
Playwright wall already solved in memory because the orchestrator never passed it on). Independent
of phase 1's recall code. `CLAUDE.md` has 0 tokens of headroom (`ci/check_instruction_budget.py`),
so this must not add a `CLAUDE.md` rule.

Hook constraints in this repo: a half-written module a guard imports takes shell access from every
live session (`reference_shared_hook_edit_bricks_live_sessions`), so write hook files in one Write
call and wire `settings.json` last; prove wiring with a nested `claude -p` run
(`reference_prove_hook_wiring_with_nested_claude`).

## Approach

- Frontmatter: `triggers: {paths: [...], skills: [...], repos: [...]}`, optional `once: true`.
- A compiler builds one trigger table (JSON) from every memory dir's frontmatter, rebuilt only when
  a memory file's mtime is newer than the table.
- PreToolUse hook on Edit|Write|Read|Skill|Agent: match tool input against the table, emit the
  matched memory body as additional context once per session per memory (session-keyed marker).
  On Agent, the text tells the orchestrator to pass it into the dispatch prompt.
- `once: true` memories are marked fired (frontmatter `fired: <date>`) after injection.
- Latency budget from the design review: under 50 ms per tool call, measured against the real
  1,637-file corpus before wiring.

## Acceptance

- Self-test covers glob, skill and repo matches, once-per-session dedupe, `once: true` retirement,
  and a stale-table rebuild.
- Measured per-call latency recorded in the commit report, under 50 ms.
- Re-run the done/1017 scenario: the meal-gap memory reaches a Clockify run without step 4a's
  manual read.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
