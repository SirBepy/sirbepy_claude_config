<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=5, reconfirm-count=1, content-hash=76b610e7 -->
<!-- duplicate-checked -->
# HubStaff token-exchange + .env update needs a reusable script, not a hand-rewritten inline block

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/clockify-reconciliator/hubstaff.md` Step 11 documents the token-exchange procedure in
prose only. Every session that needs it currently hand-writes the same ~15-line PowerShell block
(read refresh token, POST to `account.hubstaff.com/access_tokens`, backup `.env`, rewrite it,
stash the access token for follow-up calls) inline, from memory, every single time it's needed
within a run. Extract this into a real script (PowerShell `.ps1` or add it to `hs_common.cjs`)
that the skill's steps 11/12 and any `hs_*.cjs` script call instead of restating.

## Context

Observed 2026-08-21/22 in a zng-app session (clockify-reconciliator, zirtue project): the
exchange+env-update block was hand-written 4 separate times in one run (PowerShell tool calls
don't persist `$env:` state or variables between invocations, so the access token can't be
exchanged once and reused across separate tool calls - it has to be re-derived, or the whole
sequence needs to happen inside one call). Two of those four attempts were ALSO denied outright
by Claude Code's own auto-mode classifier (mid-run, non-deterministically - one denial, then a
retry of the same shape went through, then a later attempt was denied again) before the actual
root cause turned out to be unrelated (HubStaff itself was down for scheduled maintenance,
confirmed via a live screenshot of their maintenance banner). Hand-rewriting the same
credential-bearing block repeatedly is also more likely to trip that classifier than a single,
consistent, previously-reviewed script would be - a stable script content is easier for both a
human and a classifier to recognize as the same legitimate action each time, versus a
freshly-generated variant of it.

This is distinct from `done/232-clockify-reconciliator-token-rotation-guard.md` (already shipped):
232 added the backup-before-write safety net for the rotation itself. This todo is about not
re-typing the whole procedure by hand every run, a different problem than write-safety.

## Approach

1. Add `skills/clockify-reconciliator/scripts/hs_get_token.ps1` (or fold into `hs_common.cjs` if a
   Node path is preferred - steps 11/12 already mix both): takes no args (or `--env-path` override),
   reads `HUBSTAFF_REFRESH_TOKEN` from `~/.claude/.env`, does the backup-first write-ahead sequence
   already documented in `hubstaff.md` Step 11 (already fixed once, see done/232), exchanges it, and
   prints ONLY the new `access_token` to stdout (never the refresh token, never write it to a
   scratch file) so a caller can capture it in one line: `$token = & hs_get_token.ps1`.
2. Update `hubstaff.md` Step 11 to call this script instead of restating the exchange logic in
   prose - the doc should show "run the script, use its stdout as the bearer token" not the raw
   `Invoke-RestMethod` shape.
3. Since PowerShell tool calls don't persist `$env:`/variables across separate invocations in this
   harness, document that the token must be captured and used within the SAME tool call (or piped
   through the script's own stdout each time) - don't design an approach that assumes state survives
   between calls.

## Acceptance

- A future HubStaff run calls one script/command for the token, not a hand-rewritten inline block.
- The refresh token value itself is never printed to stdout or written to any file other than
  `~/.claude/.env` (and its `.env.bak`).
- `hubstaff.md` Step 11 references the script instead of restating the request shape inline.

## Notes

- Not urgent - the hand-written version works, just wastes tokens and adds classifier-trip risk
  each time it's rewritten. Low complexity, small win.
