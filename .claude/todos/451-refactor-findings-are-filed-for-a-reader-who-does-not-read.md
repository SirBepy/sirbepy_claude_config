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
