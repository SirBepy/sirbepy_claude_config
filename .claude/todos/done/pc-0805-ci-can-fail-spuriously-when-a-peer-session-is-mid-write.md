<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=2, content-hash=ab781c22 -->
<!-- duplicate-checked -->
# ci/run_all.py can report FAIL because a concurrent session was mid-write, with no way to tell

**Type:** task
**Origin:** ai

## Goal

Make a `ci/run_all.py` failure distinguishable from a concurrent-session artifact, so a run does not
either chase a phantom or dismiss a real break as "probably just a peer."

## Context

Observed 2026-08-26 in `~/.claude` during an `/autopilot` backlog run, with three of this session's
own builder subagents plus at least one other Conductor session live in the same checkout.

`python ci/run_all.py` printed:

    FAIL: 1 of 4 checks failed: hook self-tests

An immediate re-run, with nothing changed by this session in between, printed:

    OK: 15/15 hook test suites passed
    OK: all 4 checks passed

Nothing this session touched goes near `hooks/`. The tree did contain `hooks/dev-backend-guard.py`
and `hooks/test_dev_backend_guard.py` as untracked files belonging to another session, so a peer
writing one of them between the two runs is the obvious explanation.

UNVERIFIED: I did not capture WHICH suite failed on the failing run, so the peer-mid-write story is
inference from timing and tree state, not a measured cause. That gap is itself the point of this
todo. Anyone picking this up should not treat the dev-backend-guard attribution as established.

**Why this is worth more than a shrug.** `/commit` step 6a treats a non-zero `ci/run_all.py` as an
ABORT: "any non-zero exit aborts the commit." In a shared checkout that makes a peer's half-written
file able to block an unrelated session's commit. The opposite failure is worse and likelier over
time: once a run learns that CI "sometimes flakes here", a real regression gets waved through on the
second attempt. A flaky gate teaches people to ignore the gate.

## Approach

1. Reproduce deliberately rather than waiting for it again: start a run of `ci/run_all.py` while
   truncating or rewriting a `hooks/test_*.py` in another process, and confirm the failure shape.
   If it cannot be reproduced that way, say so and consider closing this rather than hardening
   against a story.
2. Make the failure legible first, before making it not happen. Today the summary line names only
   the CHECK ("hook self-tests"), not the suite, so the failing run left no evidence at all. Have
   the runner print the failing suite name and its captured output in the summary block, not only
   in the per-suite stream that scrolls past. This is the highest-value part and is worth doing on
   its own even if nothing else here lands.
3. Only then consider whether it should tolerate the race. Options, and this is the real judgment
   call, so record the reasoning: (a) do nothing beyond item 2 and let the reader decide, (b) have
   the runner skip untracked `test_*.py` files, (c) retry a failed suite once and report clearly
   that it passed on retry. **Recommended: (a) plus (b).** A retry is exactly the mechanism that
   trains people to ignore the gate, and an untracked test file is by definition not yet part of
   the committed contract CI is supposed to protect.
4. If (b) lands, it changes what CI covers, so it needs saying out loud in `/commit` step 6a and in
   whatever documents `ci/run_all.py`. An untracked hook test silently not running is its own trap.

## Acceptance

- A failing `ci/run_all.py` names the specific suite and shows its output in the final summary,
  proven by deliberately breaking one suite and reading the output.
- Whatever is decided for item 3 is written down where a reader of the failure will see it.
- A normal green run's output is unchanged apart from any added failure detail.
- `python ci/run_all.py` passes, and every existing suite still runs (count the discovered suites
  before and after: it was 15 hook suites and 1 tool suite on 2026-08-26).

## Notes

- The runner is `ci/run_all.py` at the repo root; the hook pass is `ci/run_hook_tests.py`.
- Do not fix this by making `/commit` tolerate a CI failure. The abort is correct; the problem is
  that the failure carries no information.
- Completed in /mega-todos wave 1, commit 6c5554e: ci/run_all.py propagates the failing suite name and output into the final summary, and run_hook_tests.py skips untracked test files so a peer session mid-write cannot fail the gate spuriously. Reproduced in a scratch repo first.
