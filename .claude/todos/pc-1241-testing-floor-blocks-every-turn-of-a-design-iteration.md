<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1160 (orphan sweep), 1163 (e2e as fast check), 1172 (scratch file false fail) are different failure modes of the same hook -->
# testing-floor-guard re-blocks every turn while tests are knowingly red during a design iteration

**Type:** skill-improvement
**Origin:** ai

## Goal
A session mid design-iteration, whose failing tests are a known, acknowledged state pending the dev's approval of the design, can end a question turn without the hook re-blocking it three times per round.

## Context
claude_usage_in_taskbar, 2026-10-23/24, Projects dashboard redesign (session 3dd2615a). Joe iterated the design for ~6 rounds through question cards ("keep working on the desktop flow until i love it"). The tests asserting the old design (20-24 of them) were deliberately left red until he locked the design, because rewriting them every round would be wasted work. hooks/testing-floor-guard.py fired on every round's turn end (attempt 1/3, 2/3, 3/3), each time re-running a 2-4 minute cargo check plus vitest, forcing an empty extra turn. The counter reset on every new edit, so each round cost 3 hook cycles. The only escape hatches are the CLAUDE_TESTING_FLOOR_SKIP env var (cannot be set for the hook process from inside a session) and a skip-flag file under hooks/ that is GLOBAL, so creating it would silence the floor for every other concurrent session too. The session declined that for exactly that reason.

## Approach
Add a per-session escape: a skip marker keyed by session id (like hooks/.session-markers/), with a required reason line, that the guard honours only for that session and that expires (say at the next commit or after N hours). Alternatively: skip the check when the turn ends with status `question` and the failing set equals the last reported failing set (no new failures since the dev was told).

## Acceptance
- A session can mark "tests knowingly red: <reason>" for itself only; another session's turn-end still runs the floor normally.
- tests in hooks/test_testing_floor_guard.py cover the per-session marker and its expiry.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /loop-todos on 2026-10-24. Its fix writes to `hooks/testing-floor-guard.py` and `hooks/test_testing_floor_guard.py`, which `hooks/sensitive-file-guard.py` gates with a permission ask; Jarvis (answering for Joe while he was asleep) deferred every hooks/settings todo to an attended session.

- [ ] [TOOLING] Run this todo in an attended session where Joe can approve the `hooks/` write prompts.
