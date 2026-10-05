<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: searched this backlog for "test", "red", "retry", "flaky" and "shared checkout". No existing todo covers attributing a failing test run. The related material is a zng-app memory (feedback_retry_a_failing_test_before_reporting_it), not a todo, and a memory is what already failed here - see Context. -->
# 1000 - A red test run in a shared checkout needs two mechanical checks before it is reported

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-24

## Goal

Give "do not report a red test until you have retried it" a mechanical form, so it fires on
evidence rather than on remembering a rule.

Filed from a zng-app session, per root `CLAUDE.md`'s allocation rule: the fix lives in the global
tree, so it belongs in this backlog and not in the project's.

## Context

Incident, 2026-09-23/24, zng-app session `7c08e909`.

A `fvm flutter test` run reported 2 failures in the v2 identity/relationship area. They were
reported to the dev as a real state of the tree, with the failing test names and the assertion
text (`Found 0 widgets with text "Verify your email to continue."`), plus an attribution: a peer's
in-flight work, since the test files and their widget sources were all dirty.

**The attribution was right and the verdict was wrong.** A peer had a hung `fvm flutter test`
process tree running about 20 minutes against those exact files. The run sampled a test file
mid-edit. A re-run gave `00:29 +380: All tests passed!`. The dev had already been told the suite
was red.

What makes this worth a todo rather than a shrug:

- The rule already existed and was already loaded. The zng-app memory
  `feedback_retry_a_failing_test_before_reporting_it` says in as many words that a first red run
  is not information in this repo. A second memory,
  `feedback_dont_accept_external_verdict_on_a_failing_test`, says to open the artifact before
  attributing. The artifact WAS opened, which is why the attribution was correct. The retry was
  not done.
- So this is not a knowledge gap and "be more careful" is not the fix. A rule that has to be
  remembered mid-flow did not survive being remembered, which is the same failure shape as the
  deleted background-watchdog rule in `refs/delegation-doctrine.md`.

The cheap mechanical signal that was available and unused: both failing test files AND their
widget sources were dirty in `git status`, and a test process was live. Either one alone is
enough to say "this run is not trustworthy, re-run before reporting".

## Second incident, the CAUSING side (2026-09-26, cueline session `4252077a`)

Folded in by `/close` rather than filed separately: same incident class, opposite role. The first
incident is about READING a contended result. This one is about CREATING one.

Two Conductor sessions shared the cueline checkout. The peer announced a full `vitest run` and asked
this session to hold. This session held the RUNNER correctly (started no suite of its own, said so
on the channel) and then **edited `src/store/projectStore.ts` and a test file under `src/store/__tests__/`
while the peer's suite was mid-collection.** The peer caught it and put it better than this session had:

> The problem is not your vitest, it is the edits. Holding the runner does not help if the tree
> moves: vitest reads each file when it reaches it, so a run that started before your write and
> finishes after it tests a mixture of both versions.

No phantom failure resulted this time, confirmed by the peer's own count (`3128` tests, unchanged),
but only by luck of ordering: the run had already collected that file before the write landed.

Why this belongs here and not in its own todo: the mechanical signal is the same one step 2 below
already names. `git status` dirt on a test file plus a live runner process is untrustworthy whether
you are the one who dirtied it or not. The gap is that the existing framing only tells the READER to
re-run; it never tells the WRITER to hold off, so two sessions can both follow the rule as written
and still produce a contended result.

## Approach

0. Cover the causing side too, not just the reading side. Whatever file this lands in should say
   both halves plainly: **before editing a file, check for a live runner in this checkout; before
   trusting a red run, check for dirt.** One probe answers both, so this is a wording change rather
   than a second mechanism. Note the asymmetry worth stating: "I am holding off running tests" reads
   as sufficient cooperation and is not, which is exactly the misunderstanding the 2026-09-26
   incident produced in a session that was otherwise coordinating carefully.
1. Decide where this belongs. Candidates, in rough order of preference:
   - `refs/process-hygiene.md`, which already owns orphan/stale-process doctrine and is already
     imported broadly. The live-test-process half is squarely its subject.
   - The testing floor in global `CLAUDE.md`, which is where "run every fast check the project
     has" already lives, and which is read every session.
   - A `PostToolUse` hook is the tempting option and probably the wrong one: it would have to
     parse arbitrary test-runner output to know a run was red. Consider and reject explicitly
     rather than silently.
2. Write the check as two commands, not as advice:
   - `git status --short <path of each failing test file and its source>` - any dirt means the
     run may have read a file mid-edit.
   - A live-test-process probe (`Get-CimInstance Win32_Process` filtered to the runner on
     Windows, `pgrep` on Unix) - a concurrent run means the result is contended.
   - If either fires: re-run before reporting anything, and say in the report that the first run
     was discarded and why.
3. Scope it to shared checkouts. In a solo repo this is overhead for a case that cannot happen,
   so gate it on the same signal `/commit` already uses: more than one live marker in
   `hooks/.session-markers/`, or a non-empty `list_peers`.
4. Do NOT widen this into a general flaky-test policy. The claim here is narrow and evidenced:
   concurrent sessions editing files while a suite runs produce phantom failures.

## Acceptance

- The check exists as named commands in one of the files above, not as a "remember to" sentence.
- The gating condition is written down, so it does not fire in a solo repo.
- The rejected hook option is recorded with its reason, so the next reader does not re-propose it.
- Re-reading the chosen file makes it obvious what to run when a suite comes back red in a
  checkout with live peers.
