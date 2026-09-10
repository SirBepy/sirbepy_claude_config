<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=1aaf3824 -->
# Deleting a UI surface orphans the probes that drive it, and nothing fast notices

**Type:** skill-improvement
**Origin:** ai

## Goal

A change that deletes or renames a UI surface finds the tracked browser probes that drive it
before the work is reported done, rather than after someone thinks to run the e2e suite.

## Context

Observed 2026-09-07 in `C:\Users\tecno\Desktop\Projects\countoff`.

A feature replaced `src/components/ProjectsModal.tsx` with a new home screen and deleted the file.
Two tracked probes were ported at the time, because their failures were noticed while iterating.
A third, `verify/take-sharing-probe.cjs`, was not: it opens the projects list via
`button[title^="Projects:"]`, a title that no longer exists anywhere. Five commits were reported
as done and verified over that gap.

Nothing in the current floor could have caught it:

- `/test` is fast-checks-only by design, and correctly so. Typecheck and build both pass: a
  Playwright selector string is not a symbol reference, so deleting the component it points at is
  invisible to `tsc`.
- `/e2e` is opt-in per `CLAUDE.md`'s testing floor ("Slow end-to-end suites are NOT part of this
  floor"), also correctly so.
- The probe was listed in `verify/README.md` and `readme-list-check.cjs` passed, because that check
  only verifies a probe is *listed*, never that it still runs.

Joe typed `/e2e` himself and it surfaced immediately. That is the only reason it was found the same
day. The failure mode is quiet and delayed, which is what makes it worth a mechanism rather than
more care.

This is a general shape, not a countoff quirk: any repo with a tracked UI-driving suite that is
deliberately outside the fast floor has the same hole. The suite is only as good as the last time
somebody remembered to run it.

## Approach

Two candidates, not mutually exclusive. Weigh cost against how often this actually bites before
building either.

**A. A grep step, in `/commit` or `/close` Phase 0.** When the diff deletes a file under a
components/views directory, or removes an `id=`/`title=`/`className` string, grep the repo's test
and probe directories for the deleted component's basename and for the removed literal. Any hit is
surfaced, not blocked. Cheap, mechanical, no browser. It would have caught this exact case: the
literal `Projects:` survived only inside `verify/take-sharing-probe.cjs`.

**B. Sharpen the floor's wording instead.** `CLAUDE.md`'s "Testing & verification floor" keeps e2e
opt-in, which is right for runtime cost, but says nothing about a change that *invalidates* the
opt-in suite. A sentence like "a change that deletes or renames a UI surface runs the suite that
drives it, cost regardless" turns this from judgment into a rule. Cheaper than a hook, but it is a
rule with no enforcement, which is the class of fix this file exists to avoid.

A is the real fix; B is what to do if A proves too noisy. Prefer A, and only add B if A gets
skipped in practice.

## Acceptance

- A deleted component whose basename or a removed selector literal still appears anywhere under a
  test/probe directory produces a visible warning before the work is reported done.
- The check runs without a browser or a dev server, so it stays inside the fast floor.
- False positives are surfaced rather than blocking, since a probe legitimately naming a deleted
  file (a comment, a migration note) must not stop a commit.

## Notes

Filed from a project session per `CLAUDE.md`'s rule that findings about the global tree go in this
backlog rather than the surfacing project's. No global files were edited from that session.

The countoff-side consequence is already fixed and committed (`9659938` ports the probe to the home
screen); this todo is only about the missing mechanism.
