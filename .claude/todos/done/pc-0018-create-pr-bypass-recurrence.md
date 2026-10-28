<!-- cleanup: last-checked 2026-08-08, complexity=HARD, reconfirm-count=2, content-hash=2475a61d -->
# Strengthen enforcement against bypassing /create-pr with raw gh

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop Claude from reaching for raw `git push` + `gh pr create` when the dev has already explicitly asked for `/create-pr`, even when that ask is phrased as a casual reply rather than a standalone slash-command message.

## Context

This exact mistake was already logged once (2026-07-07, PR #93, memory `feedback-use-create-pr-skill-not-raw-gh.md`) and recurred verbatim in session 2026-07-14 (PR #126, Fibo `feature/e2e-check-skill` branch). Joe's message was "yeah /create-pr, i allow it" - a literal `/create-pr` token embedded mid-sentence, not a bare `/create-pr` at message start. Claude read it as generic "go ahead" approval and ran `git push` + `gh pr create` directly, skipping the skill's tiering, anti-bloat rules, and preview/approval gate a second time.

A memory update alone (see `feedback-use-create-pr-skill-not-raw-gh.md`, "Recurred 2026-07-14" section) clearly wasn't sufficient the first time to prevent a repeat - this needs an actual enforcement mechanism, not just a stronger-worded note.

## Approach

Options to evaluate (pick one, don't just re-word the memory again):

1. A `PreToolUse` hook on `Bash`/`gh pr create` in this repo's `.claude/settings.json` that blocks raw `gh pr create`/`gh pr edit` calls outright when a `.claude/skills/create-pr/SKILL.md` exists, forcing the Skill tool path instead (self-enforcing, doesn't rely on Claude remembering).
2. A lighter-weight check: before any `gh pr create`/`gh pr edit` Bash call, grep the recent conversation for a literal `/create-pr` token - if found and the Skill tool wasn't invoked with that skill, treat it as a broken invocation and route through Skill instead of Bash.

Given hooks are enforced by the harness rather than Claude's own memory, option 1 is more likely to actually close the gap.

## Acceptance

A future session where the dev types (or embeds) `/create-pr` in a message reliably results in the Skill tool being invoked with `create-pr`, never a raw `gh pr create`/`gh pr edit` Bash call.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 95; renumbered to 18 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: scope should shrink. A hook that landed since filing,
  `hooks/flagged-skill-mention.py`, now inlines a flagged skill's full SKILL.md as additionalContext
  whenever its `/name` appears anywhere in the first line of a prompt (unanchored `re.search`). That
  substantially closes the original "embedded mid-sentence `/create-pr`" failure mode. What remains
  unmet is only the literal acceptance criterion: no `PreToolUse` hook hard-blocks a raw `gh pr create`
  / `gh pr edit` Bash call. Recommend narrowing this todo to just that hard block rather than
  re-solving the mention problem.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: new `PreToolUse` hook mirroring `commit-guard.py`, blocking raw `gh pr create` and
  `gh pr edit` unless `create-pr/SKILL.md` wrote a fresh marker immediately before the call, plus
  that marker write added to the step that runs those commands. This is the todo's own option 1.
  Scope note already recorded separately: `flagged-skill-mention.py` has since closed the mention
  half, so only the hard block remains. This was produced by a strict second-pass re-triage that
  specifically asked whether a defensible answer exists without the dev; it concluded yes. Not
  executed only because the session ended.
- Shipped 2026-08-11, wired in commit f9055ac. hooks/pr-guard.py mirrors commit-guard's marker mechanism for gh pr create and gh pr edit; /create-pr now writes a .pr-marker before each call. Read-only gh pr subcommands allowed, and gh pr comment/review deliberately left ungated so /code-review --comment keeps working.
