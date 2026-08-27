<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Nothing checks that a dispatch's task list covers every item in the todo it came from

**Type:** skill-improvement
**Origin:** ai

## Goal

Close the gap in `refs/delegation-doctrine.md` between "did every ITEM in the batch get a
dispatch" (covered) and "did every STEP in one todo reach its builder" (not covered).

## Context

Hit live 2026-08-26 in `~/.claude` during an `/autopilot` run, on todo `465`.

The orchestrator read `465`, which has a five-item Approach section, and paraphrased it into a
four-item TASK list in the dispatch prompt. Item 2 (an oracle constraint: the completion oracle may
only restate criteria the request contained, never add an action) was silently dropped. Nothing
noticed. The builder completed its four items correctly and CI was green, so every mechanical
signal said done.

**It was caught only because the dispatch asked for out-of-scope findings and the builder used that
channel honestly**, reporting: item 2 "was in the full todo spec but was NOT included in this
dispatch's explicit 4-item TASK list, so it was deliberately left untouched." Without that
volunteered note the todo would have been archived four-fifths done, with a completion note
claiming otherwise.

**Why the existing rule does not catch it.** `refs/delegation-doctrine.md` has a "Fan-out
reconciliation" section, and it is explicitly about the wrong axis: "Partitioning a batch into
dispatches by hand drops items silently... write the union of ids assigned across every group and
diff it against the source list." That protects a set of TODOS across many dispatches. It says
nothing about a set of STEPS inside ONE todo reaching one builder. Both are silent set-difference
failures with the same shape; only the first is guarded.

The paraphrase is not the bug on its own. Rewriting a todo's Approach into a dispatch's own words is
usually correct, because a builder needs different framing than a backlog reader. The bug is that
nothing diffs the rewrite against the source afterwards.

## Approach

1. Add one requirement to `refs/delegation-doctrine.md`'s "Dispatch discipline" list: when a
   dispatch is built from a todo file, enumerate that todo's Approach and Acceptance items and
   confirm each appears in the dispatch prompt or is EXPLICITLY excluded in it with a reason. Cite
   the `465` incident, since the doctrine's other rules all carry their incident.
2. Extend the "Fan-out reconciliation" section rather than starting a new one, and say plainly that
   it applies at two scales: across dispatches (ids) and within one dispatch (steps). Keeping them
   together is what stops a reader thinking the id-level rule already covers this.
3. Strengthen the out-of-scope-findings requirement, which is what actually caught this. It
   currently asks for findings outside the dispatch's lane; add that a builder should also report
   anything in the SOURCE todo that the dispatch prompt did not ask for. That makes the rescue
   deliberate instead of lucky. This is the highest-value item here: it worked once already.
4. Consider whether `refs/builder-preamble.md`'s static block should carry item 3's sentence, so it
   reaches builders without the orchestrator remembering. Lean yes, for exactly the reason todo
   `791` gave: a requirement that lives only in doctrine prose does not reach the builder.
5. Do NOT propose a mechanical check. There is no machine-readable link from a dispatch prompt back
   to a todo id, and `hooks/dispatch-preamble-guard.py`'s three checks are cheap literal string
   matches. A fourth marker cannot express "covers every item in a file it cannot identify". Record
   this reasoning so it is not re-litigated.

## Acceptance

- The doctrine names the within-one-todo case, with the `465` incident attached.
- The out-of-scope-findings requirement explicitly includes source-todo items the prompt omitted.
- Whatever lands in `refs/builder-preamble.md` is quoted in the pasted block, not just described in
  the doctrine (`791`'s lesson).
- `python ci/run_all.py` passes. State that it does not check any of this, since these are prose
  files, so a green run is not evidence the change is any good.

## Notes

- All edits are to `refs/*.md`. Nothing here writes to `hooks/` or `settings*.json`, so this is safe
  for an unattended run.
- Related: `791` (a requirement in doctrine prose never reached builders, fixed by moving it into
  the pasted block). Same root cause, different requirement. Read its `done/` file first; the
  argument for item 4 is already made there.
