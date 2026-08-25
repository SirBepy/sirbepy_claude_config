<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /mega-todos hands builders scout file sets nothing ever existence-checks

**Type:** skill-improvement
**Origin:** ai

## Goal

`/mega-todos` Step C's scout produces the `files` list that becomes each builder's owned-file set and
the input to lane partitioning. Nothing verifies those paths exist. When they are wrong the builder
cannot do its job, and the lane map was computed from fiction.

## Context

Measured 2026-08-20 in a 31-builder `/mega-todos` run in `claude_usage_in_taskbar`.

**Five of roughly 30 dispatches hit a wrong file set.** The sharpest case: todo 675's owned set named
`src/shared/chat/turn-footer.ts`, which **does not exist**. The turn footer is owned by
`turn-chips.ts`'s `TurnFooterRegistry`. The same dispatch also named `daemon/state.rs` for turn
status, which has nothing to do with it (`ReportedStatus` lives in `sessions/registry_turn.rs`), and
pointed at `mcp/server.rs` for the MCP schema, which lives in `mcp/tool_schemas.rs`. Three of four
assigned files could not carry the feature and the fourth was fictional, so only the security guard
landed. Todos 682, 698, 661 and the 661 remainder each hit a smaller version of the same thing.

The run recovered because every dispatch carried an explicit stop-and-report clause, so those five
returned accurate diagnoses instead of half-built features. **That is a mitigation, not a fix** - it
converts a wrong file set from a silent defect into a wasted dispatch, and the dispatch is still
wasted.

Two contributing causes, and the second is the more interesting one:

1. **SKILL.md already forbids the behaviour but provides no mechanism.** Step C says: *"A todo whose
   file set the scout could not pin down goes in its own lane, alone. Never guess."* A scout has no
   incentive to report "could not pin down" and no instruction to run an existence check, so it
   guesses plausibly instead. A rule with no enforcement path is the exact shape `/cleanup-todos`'s
   own rubric scores as churn.
2. **That run merged Step C's dedicated lane scout into the earlier triage pass** (one agent per ~27
   todos producing bucket, worth, validity AND file set) to avoid four full reads of an 80-todo
   backlog. That merge is a defensible token trade and was reported at the time, but it is very
   likely what degraded file-set quality: an agent triaging 27 todos will not open every cited path,
   whereas one scouting a handful might. **Do not assume this without testing it** - see step 1 below.

## Approach

1. **First, establish which cause dominates.** Re-run a small scout both ways over the same 5-10
   todos - merged into triage, and standalone - and compare how many returned paths actually exist.
   If the standalone scout is no better, the fix is entirely mechanism (item 2) and the merge is
   exonerated. Do not rewrite the skill before this is known; the merge is the convenient culprit,
   not a demonstrated one.
2. **Add the mechanism regardless of what step 1 shows.** Require the scout to `Test-Path` / `ls`
   every path it returns and mark each `verified` or `unverified`. Then have Step C's partitioner
   treat any todo with an unverified path exactly as SKILL.md already says: its own lane, alone. This
   is cheap, and it makes the existing "never guess" rule enforceable instead of aspirational.
3. Consider having the orchestrator spot-check the union of returned paths in one batch before
   dispatch. One `ls` over the whole set catches a fictional filename for near-zero cost and does not
   depend on the scout cooperating.

## Acceptance

- A scout that returns a nonexistent path is caught before any builder is dispatched, not by the
  builder. Prove it by seeding a fake path into a scout result and confirming the run isolates or
  rejects that todo.
- The `verified`/`unverified` distinction actually reaches the lane partitioner rather than being
  reported and ignored.
- A run whose scout paths are all real behaves exactly as today, with no extra dispatches.

## Notes

- Keep the stop-and-report clause in the builder preamble regardless. It is what turned this from five
  broken features into five accurate reports, and it stays valuable even once file sets are verified.
  Evidence recorded in `claude_usage_in_taskbar`'s memory
  `feedback_subagents_degrade_product_to_pass_tooling.md`.
- Related: todo 412 (the commit prefilters are blind to submodule contents), found in the same run.
- Fixed 2026-08-25, approach steps 2 and 3 shipped: the scout must Test-Path every returned path and mark it verified/unverified, the main thread re-checks the union in one batch before dispatch, and a todo with any unverified path does not dispatch at all. Step 1's two-arm experiment was NOT run as specified - instead this session's own MERGED triage scout (15 todos, triage plus file sets in one pass) was measured: 26 of 26 returned paths existed, 100 percent. That partially exonerates cause 2 (the triage merge), but it is NOT a clean comparison - my scout was explicitly told the write-target was its most valuable output and had a 30-call budget over 15 todos, versus one agent over ~27 todos of an 80-todo backlog in the failing run. Scale and emphasis both differ. Also added the budget-and-report-partial instruction after three scouts died silently in this session and a budgeted replacement over the same material returned cleanly.
