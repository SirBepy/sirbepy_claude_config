<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=d93e1785 -->
# /create-todo should check backlog CONTENT for overlap, not just titles

**Type:** skill-improvement

## Goal

Strengthen `/create-todo`'s dedup guidance so it catches content-level overlap
with existing todos, not just title-level near-duplicates - this is a
project-agnostic skill gap, not Fibo-specific, so the fix belongs in the
skill file itself.

## Context

Incident (2026-07-27, this Fibo repo): wrote todos 139-146 (a v2 frontend
migration plan) in a worktree with a small local `.claude/todos/` backlog,
without cross-referencing the much larger pre-existing main-checkout backlog
(100+ items). Missed two direct, consequential overlaps: todo 53 had already
settled (2026-07-07) exactly the `@fibo/ui`-packaging question a new todo
posed as a wide-open 3-way decision; todo 46 already had a thorough
"should we adopt Storybook, and which tool" analysis that a new todo
duplicated from scratch. Joe caught this only after handing the plan to
another AI, who - lacking the context that was already sitting in the
backlog - had to stop and ask him things that were already decided weeks
earlier. A whole extra discovery-and-repair pass (an Explore-subagent sweep +
rewriting 6 files) was needed to fix it after the fact.

The skill file (`C:\Users\tecno\.claude-personal\skills\create-todo\SKILL.md`)
already has an anti-pattern bullet: "Re-filing an existing todo - skim
`.claude/todos/*.md` titles first; if a near-duplicate exists, say so and
skip (full dedup is `/batch-todos`'s job)." This only catches EXACT
re-filing of the same task. It does not catch the more common and more
damaging case: a NEW todo whose subject matter overlaps with an EXISTING
todo's already-settled decision or already-gathered evidence, without being
a duplicate task per se (todo 139 wasn't a duplicate of todo 53 - it was a
different task that happened to re-litigate a question 53 had already
closed).

## Approach

Edit `create-todo/SKILL.md`'s anti-patterns section (or add a new step) to
require, before finalizing new todo CONTENT (not just before filing, and not
just a title skim): grep the destination backlog for keywords tied to the
new todo's subject (tool names, component names, the specific technical
question being posed) and read any hits in full. If a match exists:
- Fold its findings into the new todo directly rather than re-deriving them.
- Or explicitly supersede it (note the old id, why it's being superseded).
- Never leave both sitting in the backlog silently disagreeing.

This should apply with extra force when:
- Multiple todos are being written in one planning pass (a `/plan-todos` or
  `/iterate-it`-derived batch), since the surface area for missed overlap is
  larger.
- The authoring session's local `.claude/todos/` view is a small/partial
  slice of a larger backlog elsewhere (e.g. a git worktree whose own
  `.claude/todos/` predates or is separate from a main checkout's - see the
  Fibo project memory `feedback-worktree-todos-not-shared` for why this
  happens structurally, not just carelessly).

Also worth considering: should `/plan-todos` itself gain a similar check when
ADDING new items to an existing PLAN.md - i.e. before appending new lines,
show the dev the FULL resulting file (not just the new lines) so a
prioritization tradeoff against pre-existing queued items is visible, rather
than silently appending underneath. This was the SECOND half of the same
incident (Joe: "you shouldve flagged to me that there were other todos in
the plan and that they would be prioritized").

## Acceptance

- `create-todo/SKILL.md` (and/or `plan-todos/SKILL.md`) has an explicit
  content-level backlog-overlap check step, not just a title-skim anti-pattern.
- The check is scoped cheaply (targeted grep + read hits, not a full-backlog
  re-read) so it doesn't turn every todo filing into a large token spend.

## Notes

This is a skill-file fix, not a Fibo-specific code change - the fix belongs
in `C:\Users\tecno\.claude-personal\skills\create-todo\SKILL.md` (and
possibly `plan-todos/SKILL.md`), not anywhere in this repo. Filed here per
this repo's own `.claude/todos/` backlog since that's where the incident was
observed and where `/close` files skill-improvement candidates by default.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 147; renumbered to 24 per the max+1 id rule. Confirmed by dev 2026-08-07.

## Notes

- 2026-08-08: replaced the title-skim anti-pattern bullet in `create-todo/SKILL.md` with the
  content-level backlog-overlap check (grep destination backlog by subject keyword, read hits in
  full, fold in or explicitly supersede). Did not touch `plan-todos/SKILL.md` - the todo's Approach
  flagged that as "worth considering", not required, and it's out of scope for this dispatch.
