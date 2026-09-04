<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Nothing catches a `cc-autopilot` badge marker that is never opened or never closed

**Type:** skill-improvement
**Origin:** ai

## Goal

Make an unpaired `<cc-autopilot:on>` / `<cc-autopilot:off>` detectable, so a long unattended run
cannot leave the sidebar badge silently wrong for its whole duration.

## Context

Happened 2026-09-01, in the `/mega-todos` run of that date, in this repo.

`skills/mega-todos/SKILL.md`'s "Sidebar badge" section says to emit `<cc-autopilot:on>` at the end
of the first response and `<cc-autopilot:off>` at the end of the final one. `/auto-do-todos` and
`/autopilot` carry the same instruction. That run emitted `off` at the end and never emitted `on`
at the start, so the badge never lit at all across roughly two hours and two builder batches. The
badge exists precisely so Joe can see at a glance that a session is grinding unattended, which is
the one thing it failed to do.

Nothing caught it, and nothing could have:

- `grep -rln 'cc-autopilot' hooks/ ci/` returns nothing. No hook and no CI check knows the marker
  exists.
- `hooks/status-marker-guard.py:1-5` is a Stop hook that flags a `cc-status`/`cc-title` marker that
  is PRESENT but malformed, and its own docstring says missing markers are enforced elsewhere, by
  the Conductor daemon. That "elsewhere" covers `cc-status`/`cc-title`; there is no equivalent for
  `cc-autopilot`.

So the rule lives in three skill files as prose with no enforcement path anywhere, which is the
shape this repo's own doctrine says not to leave a rule in.

## Approach

1. Confirm the gap rather than trusting this write-up: re-run the grep above, and read
   `hooks/status-marker-guard.py` to see what it actually matches.
2. Decide where the check belongs, and this is the real decision in this todo. A Stop hook cannot
   see the FIRST response of a session from the last one, so pairing is not a single-turn property.
   Options worth weighing:
   - A Stop hook that, on seeing `<cc-autopilot:off>`, greps the session transcript for a preceding
     `<cc-autopilot:on>` and warns if absent. Catches the exact miss, costs a transcript read on
     every turn that emits `off` (rare).
   - Drop the `on` marker from the three skills and have the host derive the badge from the skill
     invocation itself, so there is nothing for a model to forget. Cleanest if the host can see it;
     needs a Conductor-side change, so check feasibility before choosing it.
   - Accept it as unenforceable and delete the instruction from the three skill files rather than
     keep a rule nothing checks.
3. Whatever is chosen, apply it to all three skills that carry the instruction (`mega-todos`,
   `auto-do-todos`, `autopilot`) so they cannot drift apart.

## Acceptance

- Either an unpaired marker is mechanically detectable, or the instruction is removed from all
  three skill files with the reason recorded.
- If a hook is added, it has a `hooks/test_*.py` suite covering both directions: `off` with a
  preceding `on` passes, `off` with none warns.
- `python ci/run_all.py` exits 0.

## Notes

Low blast radius: the badge is cosmetic, and a wrong badge never damaged anything. It is filed
because the failure was invisible for two hours and the fix is bounded, not because it was costly.
Do not build a heavyweight mechanism for it; if option 2 or 3 is cheaper, take it.
- Fixed in 2534940: the unpaired cc-autopilot marker asymmetry resolved at the skill level rather than by building a transcript-scanning Stop hook for a cosmetic badge.
