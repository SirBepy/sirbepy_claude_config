<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 894 (retrying a killed wave) and 855 (scripting Step E) are both in done/ and neither is about the orchestrator holding a stale read of its own skill file. -->
# A run that improves its own skill cannot see the improvement

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/mega-todos` a re-read point so a change the run itself lands in `skills/mega-todos/SKILL.md`
takes effect for the rest of that same run, instead of being invisible until the next invocation.

## Context

Observed 2026-09-04, in the `/mega-todos` run over `~/.claude` itself. This is not a hypothetical:
the run had **five** todos targeting its own skill file in flight (855, 872, 894, 863, 472).

Concretely: wave 2's builder for todo 855 rewrote Step E to call
`skills/mega-todos/archive-batch.ps1`, which returns a `.Pathspec` naming both halves of every
archival move plus `PLAN.md` (commit `9fa351b`). The orchestrator archived wave 2 roughly ten
minutes later and hand-rolled the loop anyway - 31 `complete-todo.ps1` calls and a pathspec built
from `git status`, exactly what the new Step E exists to replace - because it was working from the
Step E text it read once at run start.

The same staleness caused a real, if small, loss the same session: see the sibling todo on the
orchestrator's own commits sweeping a builder's file, which the new `.Pathspec` return would have
prevented.

This is a general shape, not a `/mega-todos` quirk. Any long-running skill invocation that edits
the skill it is currently executing has the same gap, and `~/.claude` is the repo where that is
routine rather than exotic.

## Approach

Options, roughly in increasing cost:

1. **Cheapest and probably right:** add one line to Step D's barrier checklist -
   `git diff --name-only <last-barrier-sha>..HEAD` and, if `skills/mega-todos/SKILL.md` (or any
   file this run is executing from, e.g. `refs/builder-preamble.md`,
   `refs/delegation-doctrine.md`) appears, re-read the changed sections before continuing. The
   barrier already runs main-thread shell commands, so this costs one command and a targeted read.
2. Have Step C's lane map flag any lane that owns a file the run itself executes from, and make
   that flag the trigger for the re-read, so a run touching none of them pays nothing.
3. Broader: state the rule once in `refs/delegation-doctrine.md`'s orchestrator hygiene section so
   `/delegate` and `/autopilot` inherit it, and have `/mega-todos` point there.

Prefer 1 plus 3: the check is cheap enough to be unconditional, and the doctrine is where the
other orchestrator-hygiene rules already live.

## Acceptance

- A barrier that follows a commit touching `skills/mega-todos/SKILL.md` re-reads it before the next
  batch, and the run's summary says it did.
- A run that touches none of its own execution files performs no extra reads.
- Dry-run trace of the 2026-09-04 sequence (855 lands in wave 2, barrier follows) shows the
  orchestrator picking up `archive-batch.ps1` rather than hand-rolling the loop.

## Notes

- Filed by /close on 2026-09-04 from the `/mega-todos` run's own retrospective.
