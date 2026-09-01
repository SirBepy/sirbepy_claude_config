<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=c4ac5c53 -->
<!-- duplicate-checked -->
# Establish which hook events reload mid-session, because two of them behaved differently

**Type:** task
**Origin:** ai

## Goal

Determine, per hook event, whether a `settings.json` edit takes effect in the session that made it.
Phase 2 saw two events disagree, and phase 6's whole plan assumes the answer.

## Context

Found 2026-08-21 during phase 2 of the harvest plan, and it contradicts what phase 1 recorded.

The belief going in, written into the plan and into a memory: "Claude Code captures hook config at
startup, so a settings edit cannot be verified from the session that made it." Phase 2 wired three
new guards into `settings.json` and then observed **both** behaviours in the same session:

- **`Bash`/`PowerShell` DID reload.** `destructive-command-guard.py` began firing on this session's
  own tool calls within minutes of being wired, and denied two of the orchestrator's own commands
  (a `grep` whose quoted alternation listed `mkfs`, and a `python -c` call carrying SQL words as
  prose). Those denials are the evidence: the guard could not have fired if the wiring were not live.
- **`Write`/`Edit` did NOT reload.** `sensitive-file-guard.py` was wired in the same edit and asks on
  any write under a `.claude/hooks/` directory. Several subsequent `Edit` calls to files under
  `C:\Users\tecno\.claude\hooks\` went through with no prompt at all. The path normalization is not
  the explanation: `check()` converts backslashes to forward slashes first, and the same guard fired
  correctly on a `.env.local` write from a nested `claude -p`.

**UNVERIFIED:** whether the split is per-event, per-matcher, ordering-dependent (the `Write|Edit`
entries were added minutes before the `Bash` one), or something else. Nothing was probed
deliberately; both observations are incidental.

Why this matters beyond curiosity: phase 6 (todos 427, 426, 434, 437) is harness surgery, and the
plan's first tip is "never let a session edit the hook currently guarding it." If `Bash` hooks reload
live, a session doing that work can be denied by a half-finished guard it just wrote, with no way to
un-wire it if the guard also blocks the shell commands needed to un-wire it. That is a deadlock, not
an inconvenience.

## Approach

1. Write one throwaway probe hook per event that emits an unmistakable marker, in `C:\tmp`, not in
   the repo. `PreToolUse` on `Bash`, on `Write`, on `Edit`, plus `PostToolUse` and `Stop`.
2. Wire ONE at a time into `settings.json`, then immediately trigger it from the SAME session and
   record fired or did-not-fire. Un-wire before moving to the next, so the results cannot be
   confounded by ordering.
3. Repeat the whole sequence once with the entries added in the opposite order, to test whether it is
   ordering rather than event type.
4. Record the result as a table in the memory entry
   `reference_prove_hook_wiring_with_nested_claude.md`, replacing this todo's UNVERIFIED note with
   the measured answer. Include the Claude Code version, since this is harness behaviour that can
   change under an upgrade.
5. If any event reloads live, add a one-line warning to `PLAN.md`'s phase 6 section naming the
   deadlock risk and the order to wire in (guard last, after the work it would police).

## Acceptance

- A per-event table exists, each row backed by a fired/did-not-fire observation, not inference.
- The ordering question is answered by the reversed-order run, not assumed.
- The memory entry is updated and its UNVERIFIED label removed for whatever was established.
- No probe hook is left wired: `git diff -- settings.json` is empty at the end.

## Notes

Do not run this probe inside a session that has real work in flight. A hook that reloads live can
block the session that wired it, and the recovery path (editing `settings.json` back) may itself be
blocked if the probe is on `Write`/`Edit`. Use a throwaway session whose only job is the probe.

Related: this is the mechanism behind `refs/harvest-2026-08-20-oss-claude-repos.md`'s note that hook
config is startup-captured, which is now known to be at least partly wrong.
