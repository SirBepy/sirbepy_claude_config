<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Refactor findings are filed for a reader who never reads them

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop producing code-quality findings that require Joe to read code before anything happens, since he
does not. Either the finding acts on itself, or it should not be filed.

## Context

Joe, 2026-08-20, on the harvest's suggestion to adopt a refactoring skill: *"but we have todos, they
get made by code-check and it suggests refactoring right? keep in mind i never end up rly reading the
code... so... i dont even ask for the refactor."*

This invalidates part of the harvest's own recommendation and is the more important of the two
`/code-check` todos. Todo 425 proposed adopting a `refactoring` skill on the reasoning that CLAUDE.md
has a "no drive-by refactors" rule with no method behind it. That reasoning assumed someone reads a
refactor finding and then requests the refactor. **Nobody does.** So a refactoring skill would sit
behind a queue that never drains, and adopting it would be motion, not progress.

The structural problem: `/code-check` writes findings into `.claude/todos/`, and the backlog contract
is explicit that Claude never auto-acts on that folder. Execution is triggered by `/pickup`,
`/batch-todos`, or Joe naming an id. For a bug, that gate is correct: Joe wants to decide. For "this
function is doing three things", the gate means it never happens, and the finding is pure write-only
cost.

Note this is NOT an argument for auto-executing everything. `/cleanup-todos` exists precisely because
ai-origin todos go stale, and memory records the rule that ai-origin todos can be archived on Claude's
own judgement while dev-origin ones always wait. The question here is narrower: **for the specific
class of finding that is mechanical, safe, and verifiable without reading code, why is it a todo at
all instead of a change?**

Candidate classes worth separating, since they have genuinely different risk:
- **Mechanical and provably safe** (dead code removal, a duplicated helper consolidated, an unused
  import) - verifiable by the test suite and a typecheck, no judgment needed.
- **Structural but contained** (splitting an over-long function, extracting a repeated block) - safe
  under a green test suite, but changes shape.
- **Genuinely a judgment call** (an abstraction is wrong, a boundary is in the wrong place) - needs
  Joe, and should stay a todo.

The first class is where the waste is. The third is where the current gate is correct.

Depends on real verification existing, which is the honest constraint: auto-applying a refactor is
only safe where a test suite can catch a mistake. Much of this repo is prose, hooks and config, where
there is no such suite. So this may only be adoptable in projects that have one, and saying that
plainly is part of the deliverable.

## Approach

1. Read `skills/code-check/SKILL.md` and inventory what it actually reports. Then read a sample of the
   code-quality findings sitting in `.claude/todos/` and `done/` and classify them into the three
   classes above, with counts. **That count is the whole argument.** If almost none are class one, the
   answer is "stop reporting class one" rather than "auto-apply it".
2. Decide the policy per class, and write it into `/code-check` itself:
   - class one: apply it, verify with the project's fast checks, report what changed in one line.
     Never file a todo.
   - class two: apply behind a green test suite only; where no suite exists, file it.
   - class three: file it, as today.
3. Add the honest exit: if a finding is class one but the project has no way to verify the change,
   **do not file it and do not apply it.** Say nothing. A finding nobody will action and nobody can
   verify is noise in a backlog that already needs `/cleanup-todos` sweeps.
4. Revisit todo 425's refactoring-skill item in light of the classification. If class three findings
   are rare, a refactoring skill is not the gap and 425's item 2 should be dropped rather than
   adopted. Record that decision either way.
5. Coordinate with todo 450, which moves the review earlier. Earlier review plus unread findings is
   still unread findings; this todo is what makes 450 worth doing.

## Acceptance

- A real count of existing code-quality findings by class, from the actual backlog and `done/`.
- A written per-class policy inside `/code-check`.
- Class-one findings are applied and verified rather than filed, demonstrated on one real case with
   the verifying command's real output.
- Where no verification exists, the finding is dropped silently, and that behavior is deliberate and
  documented.
- Todo 425's refactoring-skill item is explicitly kept or dropped, with the reason.

## Notes

The instinct to preserve here is Joe's, not the harvest's: a finding that needs him to read code is a
finding that will not happen. That is a fact about the workflow, not a failing to be corrected, and
the tooling should be built around it.

Resist auto-applying class two or three to seem thorough. The gate exists for good reasons on those,
and this repo has no test suite to catch a mistake in most of its own files.

## Result, 2026-08-22

**The count came back against this todo's own premise, so read that first.**

Population: 18 `/code-check` findings across 407 todo files (95 live + 312 `done/`). Provenance was
recovered two ways, since `/code-check`'s output template writes no provenance line: a prose line
inside the file ("Found by `/code-check` on <date>"), or a filing commit that names it (`92e6777`
filed 315-316, `f7bfa0c` filed 399-402). **18 is a floor, not a census** - a finding filed with
neither marker is indistinguishable from any other ai-origin todo.

| Class | Findings | Executed | Dropped | Open |
|-------|----------|----------|---------|------|
| 1 - mechanical | 4 (287, 382, 400, 402) | 2 | 0 | 2 |
| 2 - structural | 10 (61, 250, 285, 288, 315, 316, 335, 380, 381, 401) | 8 | 1 | 1 |
| 3 - judgment | 3 (286, 334, 399) | 2 | 0 | 1 |
| not a code-quality finding (a real defect) | 1 (289) | 1 | 0 | 0 |
| **total** | **18** | **13** | **1** | **4** |

The four open ones (399-402) were all filed 2026-08-19, three days before this count.
`done/335` is the `-marker-consume-block-` file; the other `done/335-` is a different todo and is
not part of this population (ids 307, 335 and 338 each name two files - a known backlog defect).

**The premise is false.** 13 of 18 filed findings were executed, 13 of 14 excluding the three-day-old
cohort. And **zero of the 13 were executed by Joe naming an id** - every one was drained by a
Claude-driven batch runner: `/autopilot` (250), same-session follow-through (285-289),
`/auto-do-todos` (315, 316, 334, 335), `/mega-todos` on 2026-08-19 (380 = `3e0fdac`, 381 =
`de55513`, 382 = `1de2284`). Joe's statement is accurate about Joe and says nothing about the
queue. "He does not read the code" and "the finding never happens" are different claims and only
the first is true. There is no write-only waste to remove.

**What shipped anyway, and why.** Two things in this todo survive the premise being wrong, because
they are about cost per finding rather than about drain rate. `/code-check` Step 4a now classifies
every finding and routes it: class 1 is applied rather than filed, class 3 is always filed, class 2
is filed unless a green suite genuinely exercises it. Joe chose this over both shipping the todo
verbatim and doing nothing (`ask_user_question`, 2026-08-22).

**The exercise test is the part that was not in this todo, and it is the important part.** While
writing Step 4a, a mechanical dead-symbol scan flagged `hooks/_hooklib.py:63`'s `strip_quotes` as
having zero references. It is live: `hooks/package-manager-guard.py:28` and
`hooks/flutter-workdir-guard.py:37` both import it as `strip_quotes as _lib_strip_quotes`, which a
name-keyed scan cannot see. Deleting it would have tripped both guards' fail-closed `except` and
blocked every npm/yarn/pnpm and flutter command in every session - **and `python ci/run_all.py`
would still have printed 4/4 green**, because `ci/run_hook_tests.py:15` discovers `hooks/test_*.py`
and neither guard has one. So "verified by the fast checks" is meaningless unless the fast checks
reach the changed lines, and Step 4a now demands the specific failing command be named before
anything is applied. Filed as todo **501**.

**The silent drop was overruled by Joe and replaced with a logged drop.** A verifier confirmed the
flaw: a misclassified finding dropped in silence leaves no todo, no commit and no log, which is
strictly worse than the filed-but-unread entry it replaces. `.claude/todos/dropped-findings.log`
is now the append-only record, added to the contract in `close/ai-todos-format.md`.

**Acceptance not met, stated plainly rather than worked around:** "class-one findings are applied
and verified, demonstrated on one real case." No such case existed to demonstrate. A fresh scan of
the only test-covered scope (`hooks/`, `tools/`, `ci/`) produced one false positive (`strip_quotes`
above) and three correctly-filed class-3 re-exports (todo 402). The one genuine class-1 finding
found anywhere was `skills/roblox-animation/bvh_to_keyframes.py:29`'s unused `import math` - the
four `math.rad(` hits at :210-218 are inside f-strings emitting Luau, not Python references - and
it sits where nothing can verify it, so Step 4a's own honest exit applied and it was logged rather
than applied. That outcome is itself evidence for the conclusion above: class 1 is rare, and the
verifiable ones are already gone.

**Todo 425's item 2 is resolved: the `refactoring` skill is NOT adopted as a skill.** Its gate
("until 451's classification shows there is a class of finding that actually reaches execution")
is literally satisfied - class 2 is the largest class and executes 8 of 10. It still loses on
mechanism, and Joe chose the alternative: fold the transferable method into the builder preamble
instead. Three reasons, each checked: `CLAUDE.md:27` states subagents cannot invoke skills, and
subagents are what drained all 13; the upstream description is 117 words against a ~25-word budget
and names four sibling skills absent here; and its load-bearing precondition is a passing-test
baseline that most of the counted executions never had (`done/285` was verified by hand-diffing
against a commit hash). Carried into 425.

Rated before deciding: 4-lens `/rate-it` panel plus the adversarial verifier pass, median **4/10**,
verdict ESCALATE. All six flaws came back CONFIRMED, none refuted. The panel killed a class-label
field before it was written - `/batch-todos` re-derives EASY/HARD/PRODUCT from file content by
design (`skills/batch-todos/SKILL.md:27`) and no runner reads any per-todo class field. One rater
claim was refuted by my own check: 399-402 were not "passed over" by the 2026-08-19 mega-todos run,
they were filed at 18:10, after it finished at 17:49.
