<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=a4c6d3d0 -->
# iterate-it: require main-agent audit gate on Phase A->B transition, matching Phase B's floor gate

**Type:** skill-improvement

## Goal

`skills/iterate-it/SKILL.md`'s Phase A (Explore) exit condition currently promotes to
Phase B (Polish) on the SUBAGENT's score alone. Phase B's own exit condition additionally
requires the MAIN agent's independent audit score to clear a floor. Bring Phase A's exit
condition in line: promoting out of Explore should also require the main audit to clear
a threshold, not just the sub's self-reported score.

## Context

Current `skills/iterate-it/SKILL.md` (as of 2026-08-01):

Phase A exit condition (line 44):
```
- **Promising**: sub score â‰Ą `--threshold` â†’ enter Phase B with the just-evolved proposal.
```
This checks ONLY the sub's score.

Phase B exit condition (line 55):
```
- **Floor hit**: sub score â‰Ą `--floor` AND main audit â‰Ą `--floor - 1` â†’ done, report.
```
This requires BOTH the sub's score AND the main agent's independent audit score
(described at line 69: `**Main audit.** After the sub returns, pick a score 1-10
yourself. Not a vote - a dissent signal vs the sub.`).

The asymmetry means a sub can inflate its own score to force an early Phase A exit
without the main agent's independent check ever gating that specific transition - the
audit still runs every round per the "Per-round flow" step 3, but its score is currently
only consulted in the Phase B floor check, never in the Phase A promotion check. This is
a sycophancy-resistance gap: the whole reason `iterate-it` runs a main audit every round
(line 108: "**Always main-audit each round.** It's the only check against sub
sycophancy.") applies equally to the Explore->Polish transition, not just the Polish->done
transition.

## Approach

1. Read `skills/iterate-it/SKILL.md` in full before editing (algorithm section,
   ~lines 33-73).
2. Change the Phase A "Promising" exit condition (currently line 44) to also require the
   main audit score to clear a threshold. Simplest symmetric choice matching Phase B's
   `--floor - 1` pattern: `sub score >= --threshold AND main audit >= --threshold - 1`.
   Confirm this exact number with Joe if picked up interactively (this todo doesn't
   pre-decide the precise offset, only that a main-audit gate must exist here) - default
   to `--threshold - 1` if resolving it non-interactively (autopilot/batch-todos), since
   it mirrors the existing Phase B pattern exactly.
3. Update the "Cap" exit condition's wording if needed so it's clear the cap-based
   promotion (round count == `--explore-max`) does NOT require the audit gate - that
   path already promotes "the best-scoring proposal so far" regardless of score, and
   should stay that way (it's a budget exhaustion fallback, not a quality gate).
4. Update `skills/iterate-it/templates.md` if it documents the exit conditions elsewhere
   (read it once, per SKILL.md line 77 - "read it once, at round 1").

## Acceptance

- Phase A's "Promising" exit line documents both a sub-score AND a main-audit-score
  condition, symmetric in shape to Phase B's existing "Floor hit" line.
- The "Cap" and "Thrash" exit conditions remain unchanged (round-count and
  PIVOT/KILL-marker based, no audit gate needed there).
- Re-read the edited section to confirm the markdown list formatting and the `--floor - 1`
  style precedent are preserved.

## Notes

- completed, commit 2d57b70
