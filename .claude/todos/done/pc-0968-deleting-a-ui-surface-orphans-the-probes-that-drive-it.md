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
- DONE 2026-09-10 via /loop-todos cycle 5, with the residual stated rather than hidden. New tools/dead-probe-check.py greps a diff removed lines for title and aria-label literals containing a colon, matched up to the colon, plus exact id, data-testid and name literals, then checks whether that literal still appears in a probe or test directory. Seconds, no browser, advisory, always exit 0. Wired into /close Phase 0, feeding any finding into the existing unfinished-commitments list so it goes through the same finish-it-first or close-anyway handling instead of being printed where nobody reads it. The measurement is the reason this shipped rather than being killed like the three guess-based hooks before it. Against countoff real history, 143 commits, in scratch worktrees so the live tree was never touched: the todo OWN proposed approach, grepping for the deleted component basename, would have caught NOTHING, because the dead selector title-caret Projects-colon never contains ProjectsModal and lived in App.tsx rather than the deleted file. A bare-word version fixed that miss but scored 9 false positives to 1 true positive, squarely in the territory that killed the earlier prototypes. Requiring the colon this codebase own convention already uses dropped it to zero false positives while still catching the incident exactly: 2 candidate literals across 143 commits, 1 finding, and it is the real one. Both directions verified against the incident commit and its fix. Residual, accepted deliberately: the only trigger is /close, not every /commit, so a session that never closes still ships the failure mode. That is the right layer for this defect, since the incident was five commits REPORTED verified, and reporting happens at close time; taxing every commit in every repo for a rare failure was not worth it. Reopen if it recurs in a session that never ran /close.

## Resolution (2026-09-10)

Built candidate A, not B: `tools/dead-probe-check.py`, wired into `skills/close/SKILL.md` Phase 0
as a new "Orphaned-probe check" bullet (that dispatch's `settings.json`, `ci/`, and
`skills/commit/` were off-limits, so `/close` Phase 0 is the only wired-in trigger point this
round - see the gap noted below).

**Rule shape, not what the Approach section guessed.** The todo's own Approach A named "the
deleted component's basename" as the first thing to grep for. Measured against countoff's real
history (143 commits, 3 UI-file deletions, the one real incident) that specific idea would have
caught NOTHING: the dead literal (`button[title^="Projects:"]`) never contains the deleted file's
name (`ProjectsModal`), and it lived in a *different* file (`src/App.tsx`, the trigger button),
not the deleted one. A bare-word version of "grep for a removed selector literal" fixed the miss
but introduced 9 false positives to 1 true positive on the same corpus (Zoom/Share/Song/Edit/One
/Add/Delete/Bring - ordinary English words recurring in unrelated probe code) - squarely the
67/55/20-25 percent territory PLAN.md's Hook doctrine section already killed three prototypes
over. Requiring the colon this codebase's own convention already uses (`title="Label: detail"`
paired with a Playwright `title^="Label:"` prefix selector) dropped that to 0 false positives
while still catching the one real incident exactly. `id=`/`data-testid=`/`name=` get an exact-match
arm with no colon requirement (0 false hits in the same corpus, though the corpus never exercised
a true positive for that arm - documented as "provably silent so far", not proven to catch
anything, in the script's own docstring).

**Verified both directions against the real incident**, using scratch worktrees at the incident
commit and its fix commit (never touching countoff's working tree): fires exactly once, on
`src/App.tsx`'s removed `title="Projects: switch, duplicate, start a new one"` vs.
`verify/take-sharing-probe.cjs`; silent on the fix commit, an unrelated 5-commit range, and a
clean tree.

**Known gap, honestly stated.** This fires on `/close` Phase 0, not on every `/commit` - `/commit`
was off-limits to edit this round, and Approach A explicitly allowed either wiring point ("in
`/commit` or `/close` Phase 0"). A session that never runs `/close` before ending still ships the
same failure mode this todo describes. Acceptance criterion 1 ("produces a visible warning before
the work is reported done") is satisfied under the reading that `/close` is this repo's own
end-of-session "reported done" ritual, not under a stricter "every single commit" reading. A
follow-up wiring it into `skills/commit/` directly, once that file is writable, would close the
remaining gap - not filed as a todo yet, flagged in the dispatch report instead.

**968 is not fully closed by this alone** - it satisfies all three Acceptance bullets under the
gap above, but the mechanism still has a session-boundary hole. Recommend archiving only once
either (a) the dev accepts the `/close`-only trigger as sufficient, or (b) a follow-up wires the
same script into `/commit`.
