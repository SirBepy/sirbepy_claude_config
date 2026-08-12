<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=2, content-hash=cd59e692 -->
# /auto-do-todos guards context but not session budget, so a fan-out can die mid-edit with nothing verified

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/auto-do-todos` (and `/autopilot`, which it adopts) from dispatching a fan-out that cannot
survive being interrupted. Two holes: it measures the wrong budget, and it has no rule for concurrent
agents editing one shared checkout.

## Context

Observed 2026-08-07 in the fibo repo, and it cost the run.

`/auto-do-todos` Step 6 checks `node ~/.claude/skills/context-left/context-left.mjs` after each todo
and hard-stops at 40% context used. That was the run's only budget guard. Context was at ~14% used,
comfortably safe, when the run dispatched 4 concurrent sonnet agents over 12 frontend2 code-health
todos (208/209/210, 185/219/197, 158/174/200, 169/171/217).

Each agent burned ~85-95k tokens, ~360k total, and then all four died simultaneously on
`You've hit your session limit, resets 7:30pm (Europe/Warsaw)`, partway through editing. **Zero of the
four delivered a report.**

The context guard could never have caught this. Subagent tokens barely touch the orchestrator's
context, which is the whole reason for delegating, while consuming the same API session budget. So a
fan-out reads as free on the only meter the skill watches, right up to the point it ends the session.

**The compounding hole.** All 4 agents were deliberately instructed NOT to run `npm run lint`, because
four agents linting one shared checkout would each see the others' in-progress edits and chase phantom
errors. That reasoning is sound, and its consequence is that the ONLY verification point in the whole
design is the orchestrator's single lint run after every agent reports. When the agents die before
reporting, that point is never reached and nothing has been verified by anyone.

The wreckage: 18 modified files, 2 new untracked files, `tsc --noEmit` failing with 5 errors (a
half-stripped `CollapseToggle.tsx` missing its `cn` import, and `Sidebar.stories.tsx` still passing
props that were deleted), eslint never having run at all because tsc gates it, and 4 of the 12 todos
left half-applied. A half-applied dedupe is strictly worse than the duplication it replaced: two
sources of truth plus a shared module. Reconstructing per-todo state took a `git status` plus lint
forensic pass, and every verdict had to be labelled INFERRED rather than reported in the handoff
(fibo todo 223).

## Approach

1. Add a **session-budget** consideration to `/auto-do-todos` Step 6, alongside the existing context
   read. Investigate what is actually queryable: `context-left.mjs` reads context, not session quota,
   so this may need a new signal or may only be expressible as a heuristic ("N agents x expected
   tokens each, against how much this session has already spent"). If no hard signal exists, say so in
   the skill and make the rule about fan-out WIDTH instead.
2. Add a rule for **concurrent agents in one checkout**: either each agent finishes and verifies one
   todo completely before starting its next, so an interruption leaves a clean boundary, or the batch
   runs sequentially. Prefer per-item completion over per-agent batching whenever a broken intermediate
   tree is expensive, which for a typecheck-gated frontend is always.
3. Add an explicit **interrupted-fan-out recovery** step: on any agent dying without a report,
   reconstruct state from `git status` plus a real lint/test run, mark every per-item verdict as
   inferred rather than reported, and file the handoff before doing anything else. The 2026-08-07 run
   did this correctly but only by improvisation.
4. Consider whether the isolation `worktree` option belongs here, so parallel agents cannot see each
   other's partial edits and each CAN self-verify. Weigh it against the known worktree hazards already
   filed (junction removal recursion, `node_modules` junctions, Vite dev-server locks breaking rebase).

## Acceptance

- The skill names session budget as a distinct resource from context, with a stated rule even if that
  rule is only "cap fan-out width", and does not imply a healthy context reading means a fan-out is safe.
- A fan-out interrupted halfway leaves either completed-and-verified todos or untouched ones, never a
  half-applied refactor across several files.
- The skill tells a recovering session how to reconstruct state and how to label inferred verdicts.

## Notes

- Recorded in memory as `feedback-size-fanout-against-session-budget` with the full token numbers.
- The same failure would hit `/autopilot` and `/delegate`, since `/auto-do-todos` adopts `/autopilot`'s
  behavior contract by reference and `delegation-doctrine.md` governs fan-out shape. Fix it where the
  contract lives rather than only in `/auto-do-todos`, or the other two keep the hole.
- Model tier was correct and is not the problem here: all four were `sonnet` per the mandatory rule.
  The problem was width and interruptibility, not cost per agent.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add a session-budget consideration to `auto-do-todos/SKILL.md`'s context-threshold
  step and to `refs/delegation-doctrine.md`, since `/autopilot` and `/delegate` inherit it. No direct
  session-quota signal is queryable, so cap fan-out WIDTH explicitly instead, which is the todo's
  own stated fallback. Add a rule preferring per-item completion over per-agent batching for
  typecheck-gated code, and an interrupted-fan-out recovery step that reconstructs state via
  `git status` plus a real lint and test run, labels reconstructed verdicts INFERRED, and files a
  handoff first. This was produced by a strict second-pass re-triage that specifically asked whether
  a defensible answer exists without the dev; it concluded yes. Not executed only because the
  session ended.
