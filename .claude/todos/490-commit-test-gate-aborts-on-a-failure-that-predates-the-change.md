<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=7, reconfirm-count=1, content-hash=94c04c83 -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "aborts the commit", "run-tests". The ancestor is
     done/383, which ADDED this gate; this is the follow-up gap that shipping it exposed.
     Not a duplicate of 383 and not an argument to revert it. -->
# /commit's test gate aborts on a red suite even when the failure predates the change

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/SKILL.md` steps 6 and 6a abort a commit on any non-zero test exit, with no way to
distinguish **"your change broke this"** from **"this was already broken before you started"**. The
second case is common on a shared branch, and the rule as written blocks unrelated work behind
someone else's red test.

## Context

Hit on 2026-08-22 in `claude_usage_in_taskbar`. Two commits were ready, both verified green in
isolation (typecheck clean, their own specs passing). Step 6a ran the project's `test` script, which
came back 916 passed / 1 failed / 2 failed FILES.

Both failures were provably pre-existing:

- `tests/event-store.test.mjs` traced to commit `1ba8ee7b`, which `git merge-base --is-ancestor`
  confirmed predated the session's start sha; neither the test nor its source changed during the
  session.
- `tests/skill-command-dedup.test.mjs` had NEVER run, a `vi.mock` factory referencing a `const` in
  its temporal dead zone, so vitest reported "no tests" rather than a failure.

The rule's text is unambiguous:

> Do not stage or commit anything until the user either fixes it or explicitly says to skip.

Following it literally means either abandoning two verified commits, or blocking on a question in a
run explicitly contracted not to ask. The run committed with a documented override and reported it.
That was the right call and the rule should not have needed overriding to get there.

**This is a gap in 383's fix, not an argument against it.** `done/383-commit-never-runs-this-repos-own-test-suite.md`
added this gate for a good reason: a broken test shipped and sat undetected for days. Keep the gate.

**Also note the second failure would defeat a naive fix.** A collect-time error yields "no tests" and
zero failed assertions, so a check comparing failure COUNTS before and after would see 0 == 0 and
call it unchanged. Whatever lands has to compare identity, not counts.

## Approach

Make the gate discriminate rather than relax. Sketch, in preference order:

1. **Compare failing-test identity against the pre-change state.** Run the suite (or read a cached
   baseline) at `HEAD` before the change, then after; abort only if the failing SET gained a member.
   Costs a second suite run, which is acceptable for a fast suite and is the honest answer.
2. **Scope the run to what the commit touches**, where the project's runner supports it, so an
   unrelated red file is out of scope by construction. Cheaper, but misses genuine breakage the
   change caused elsewhere.
3. At minimum, if neither is feasible: allow proceeding when every failure is shown to predate the
   session, **require** that the evidence is recorded in the commit's report, and keep the hard abort
   for any failure that cannot be proven pre-existing. This is what the run did by hand.

Whichever lands, the unattended case needs an explicit answer. `/mega-todos` and `/auto-do-todos` runs
have nobody to ask, and the current wording sends them into a question that cannot be answered. The
unpushed-overlap check in step 8 already models this well: it defines an attended branch and an
unattended branch that proceeds and records. Mirror that shape.

## Acceptance

- A commit whose own changes are green is not blocked by a failure that provably predates the
  session, and the evidence for "predates" is recorded rather than asserted.
- A commit that genuinely breaks a previously-passing test is still hard-blocked.
- A test file that fails at COLLECT time (reporting "no tests", zero failed assertions) is correctly
  treated as a failure, not as an unchanged count.
- The unattended path is defined explicitly and does not route to `AskUserQuestion`.
