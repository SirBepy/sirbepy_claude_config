<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Finish the outbound gate: cover updates, move the mutation guard, wire /linear's pointer

**Type:** task
**Origin:** dev

## Goal

Close the three gaps left after the Linear create gate shipped on 2026-08-18 in `400d1e1`, so
every outbound ticket write on the two platforms Joe cares about passes the same ground check.

## Context

Joe picked the shared outbound gate as the first build of the verb-first restructure, on the
reasoning that it is the one item backed by a real incident (2026-08-14, a ticket filed for work
already done) rather than by taste.

**What already shipped in `400d1e1`:**

- `refs/outbound-ground-check.md` - the platform-agnostic ground check. Queries 1 and 3 (merged
  PRs, the claim at the tracked branch) were already platform-agnostic and were lifted unchanged.
  Query 2 (tracker search) has per-platform sections for Shortcut and Linear.
- `hooks/linear-create-guard.py` - blocks `issueCreate` without a fresh marker. Verified with 9
  cases: unrelated command passes, a Linear READ query passes, create blocks with no marker,
  create passes with a marker, the marker is consumed, the next create blocks again.
- `hooks/shortcut-create-guard.py` now accepts the shared `.outbound-marker*` AND the legacy
  `.shortcut-marker*`, so nothing that existed before changed behaviour.
- Architecture chosen by Joe: **one guard per platform**, sharing a marker and the ref, so a regex
  mistake in one can never disarm the other.

**Obsidian is explicitly out of scope.** Joe, 2026-08-18: *"obsidian isnt important at all, we can
just focus on the 2 platforms that matter to me, later when i need obsidian, i can ask an ai to add
obsidian."* Do not add it unless he asks.

## Approach

**1. Gate updates, not just creates.** `refs/outbound-ground-check.md` already specifies the rule
in its "Updates are a different question" section: on an update, only ONE hard stop carries over,
query 3 finding the claim absent at the tracked branch. "Somebody already did this" is not a reason
to stop an update, since the ticket exists because the work is live. Queries 1 and 2 are
informational there. Build the enforcement to match that spec; do not re-derive it.

Shortcut updates already route through `guard_mutation.py` (see step 2). Linear updates go through
`issueUpdate` and have no guard at all yet.

**2. Move the mutation guard out of the skill directory.** `settings.json:180` (line number as of
2026-08-18) hardcodes:

```
python "C:\Users\tecno\.claude\skills\shortcut-create-ticket\hooks\guard_mutation.py"
```

That guard lives INSIDE a skill folder, so any merge, rename or relocation of
`shortcut-create-ticket` silently disarms it - no error, the gate just stops firing. Every other
guard lives in `hooks/`. Move it there, update the settings line, and confirm the hook still fires
before considering it done. **This matters more than it looks: `/ticket` (todo 351) would relocate
exactly that directory.**

Note the sibling line, `settings.json:171`, is NOT affected - it points at `hooks/shortcut-create-guard.py`,
which is already in the right place.

**3. Wire the pointer into `/linear`.** `skills/linear/SKILL.md` should name the ground check before
its Create recipe, the way `shortcut-create-ticket` does. **This was deliberately NOT done on
2026-08-18** because another session had uncommitted changes in that file (an ownership-gate change
allowing self-assign of unassigned tickets). Re-read it before editing; that work may have landed.

Enforcement does not depend on this step - the guard's deny message already names
`refs/outbound-ground-check.md`, so a blocked session self-corrects. It is a nicety, not the gate.

## Acceptance

- A Linear `issueUpdate` and a Shortcut story update both require a fresh marker.
- An update whose claim IS present at the tracked branch passes; one whose claim is absent blocks.
- `guard_mutation.py` no longer lives under `skills/`, and its hook still fires after the move.
- Creates on both platforms behave exactly as they do today; the legacy `.shortcut-marker*` name
  still works.

## Notes

- **Known false positive, do not "fix" it by loosening the match:** both guards match on the command
  STRING, so any command that merely mentions the endpoint and mutation name is blocked, including a
  test for the guard itself. Hit while testing on 2026-08-18. Use the bypass env var
  (`CLAUDE_LINEAR_CREATE_HOOK_BYPASS`, `CLAUDE_SHORTCUT_CREATE_HOOK_BYPASS`) or assemble the string
  at runtime. This is the same trade the Shortcut guard has always made and it is the safe direction
  to err in.
- The ground check's precision is deliberate. From the original file: *"a gate that fires on maybes
  trains the dev to click through, which turns stopped back into informed."* Keep hard stops narrow.
- Related: [[351-unify-ticket-skills-behind-one-platform-inferring-entrypoint]] is the larger
  verb-first `/ticket` work this gate is meant to sit underneath.
- Completed 2026-08-18. Scope narrowed by Joe mid-build: updates are gated only when CLAIM-BEARING (name/description/comment), not on state moves or self-assign, per the narrow-hard-stops doctrine in refs/outbound-ground-check.md. Shipped: hooks/linear-update-guard.py, claim-bearing gate added to hooks/shortcut-mutation-guard.py, and that guard moved out of skills/shortcut-create-ticket/hooks/ (git rename, 87% similarity) so /ticket can no longer disarm it. STILL OPEN: the /linear SKILL.md pointer, blocked both times because a concurrent session has uncommitted changes in that file; enforcement does not depend on it since the deny message names the ref. Two bugs found and fixed on the way: a broken test shipped in 400d1e1, and ~/.claude/.env's UTF-8 BOM which made the owner check fail closed on EVERY Shortcut mutation.
