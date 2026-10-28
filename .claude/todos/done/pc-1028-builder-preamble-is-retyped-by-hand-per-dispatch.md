<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=803b66f6 -->
<!-- duplicate-checked: grepped this backlog and done/ for "preamble", "dispatch", "builder" and "dispatch-preamble-guard". Entries about the guard HOOK concern what it checks; nothing covers the orchestrator-side cost of composing the block. refs/builder-preamble.md exists as the paste source, which is the thing this todo says is not enough. -->
# The builder preamble is retyped by hand into every dispatch

**Type:** skill-improvement
**Origin:** ai

## Goal

An orchestrator composes a compliant builder preamble by supplying the few values that actually vary,
instead of reproducing a ~60-line block per dispatch.

## Context

Measured 2026-09-26 on one `/loop-todos` run in `claude_usage_in_taskbar`: **11 builder dispatches
across 5 cycles**, each carrying the full preamble from `refs/builder-preamble.md`. That is roughly
**600-700 lines of prompt text authored by hand** in a single session, for a block whose per-dispatch
variation is four things:

- the working directory
- which staging line applies (shared git index or not)
- the per-lane OFF LIMITS file list
- the screenshot-subfolder id, or the `READ-ONLY DISPATCH` marker instead

Everything else is fixed text. `refs/builder-preamble.md` already exists precisely so it is not
retyped from memory, and its "Placeholder table" names those four slots - but the mechanism is still
"read the file, copy the block, substitute by hand", so the cost and the drift risk both scale with
dispatch count rather than with the number of distinct lanes.

**Why this is worth fixing rather than tolerating**, in order of how much each actually bites:

1. `hooks/dispatch-preamble-guard.py` is a pure string check on three markers. A hand-copied block
   that loses one is rejected, and the failure arrives as a blocked dispatch after the prompt was
   already composed - the expensive moment. The guard exists because drift already happened once (the
   `bdb0323` incident named in the ref file).
2. Every line of it is orchestrator context spent on text that could be assembled. On a long run this
   is a real fraction of the budget, and it competes with the thing the orchestrator is actually for.
3. The four varying values are exactly where a mistake matters - a stale OFF LIMITS list is how two
   lanes collide - and they are currently buried in sixty lines of boilerplate where they are hard to
   review at a glance.

## Approach

**Settle the mechanism question first; the rest is mechanical.** A subagent prompt is a string passed
to the `Agent` tool, so there is no hook that can expand a placeholder for us. Candidates:

1. A small script (`skills/_shared/` or `tools/`) that takes the four values and prints the composed
   block, so a dispatch becomes "run it, paste its stdout". Cheapest, keeps one source of truth, and
   the guard's three markers are then structurally present rather than hopefully present.
2. Leave the text alone and add a one-line checklist at the top of `refs/builder-preamble.md` naming
   only the four slots, accepting the copying cost. Weakest, but honest if option 1 turns out to need
   its own maintenance.
3. Shorten the block itself by moving the genuinely universal half (orphan check, prefilter gate,
   no-`run_in_background`) behind a single referenced line. **Check whether the guard can still see
   its markers before considering this** - the guard is a literal string check, so indirection likely
   breaks it, which may rule the option out entirely.

Whichever is chosen, verify against the guard for real: compose a dispatch with the new mechanism and
confirm it is accepted, rather than reasoning that the markers are present.

## Acceptance

- A dispatch's per-lane prompt names the four varying values and does not restate the fixed block.
- `hooks/dispatch-preamble-guard.py` accepts a dispatch built the new way, proven by an actual
  dispatch, not by inspection.
- `refs/builder-preamble.md` remains the single source of the text, whatever assembles it.
- `python ci/run_all.py` passes.

## Notes

- Do NOT solve this by trimming the preamble's content to make copying cheaper. Each paragraph traces
  to an incident, and the ref file says so; the problem is the copying, not the length.
- Related, same session, different cost: `hooks/agent-todo-write-guard.py` blocks a builder from
  writing its own `## Decided` block into `.claude/todos/`, so the orchestrator hand-applied **6** of
  them from report text in that same run. That is a second manual tax with the same shape, and it is
  worth deciding whether a builder should get a staging file it CAN write. Not folded in here because
  the fix is a different hook and a different contract; file separately if it recurs.

- Supporting evidence folded from archived duplicate 1006 (/cleanup-todos 2026-10-05): reading `refs/builder-preamble.md` in the same turn, right before drafting a dispatch, fixed preamble compliance on one run, which argues for a composer that reads the file rather than relying on memory.
- Completed by /loop-todos cycle 1 (2026-10-05), lane L6; 1028 tested by tools/test_build_dispatch.py (RED: unknown -NoCommitBlock, GREEN 13/13), and auto-do-todos now points at the composer.
