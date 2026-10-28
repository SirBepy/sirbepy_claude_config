<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Multi-account CLI wrappers (temporary manual account switching)

**Type:** task

## Goal

Extend the existing model-tier wrappers (`claude`, `claude-light`, `claude-mid`, `claude-heavy`)
into per-account families, e.g. `claude-fibo`, `claude-fibo-light`, `claude-fibo-mid`,
`claude-fibo-heavy` (and the same for a work account), so a terminal session can pick WHICH
Claude account it runs as, at any tier, with no logout/login. Temporary manual bridge until the
in-app Claude Conductor multi-account feature ships.

## Context

- The current `claude` / `-light` / `-mid` / `-heavy` wrappers set model + effort tiers, defined
  in `$PROFILE`.
- Account-switch primitive (decided in the Conductor multi-account brainstorm, 2026-07-01): set
  `CLAUDE_CODE_OAUTH_TOKEN` per invocation. It is a long-lived subscription token minted once via
  `claude setup-token` while logged into that account; silently overrides
  `~/.claude/.credentials.json` and bills to that account's Pro/Max/Team subscription (NOT
  metered). Env vars are per-process, so several terminals can each be a different account from
  ONE shared `~/.claude`. Precedence: `ANTHROPIC_API_KEY` > `CLAUDE_CODE_OAUTH_TOKEN` >
  `.credentials.json` - wrappers must ensure `ANTHROPIC_API_KEY` is unset.
- Rejected alternative: a separate `CLAUDE_CONFIG_DIR` per account (duplicates the config dir).

## Approach

Per account `<acct>`: run `claude setup-token` logged in as that account once, store the token
securely OUT OF BAND, then generate `claude-<acct>` (default tier) plus `-light`/`-mid`/`-heavy`
variants that export `CLAUDE_CODE_OAUTH_TOKEN` (and unset `ANTHROPIC_API_KEY`) before calling the
same tier logic the base wrappers use.

## Status: DONE - verified implemented, filed straight to done/

Verified 2026-07-17: `$PROFILE`
(`C:\Users\tecno\OneDrive\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`) contains
`New-ClaudeAccountWrappers` (factory function, line ~89) and `New-ClaudeAccountWrappers -Account
fibo` (line 106) wiring up the `fibo` account. Implementation details and decisions (token storage
via Windows Credential Manager, `$global:ClaudeTiers` as shared source of truth, work account
deliberately not scaffolded) are recorded in memory `project_multi_account_claude_wrappers` and
`reference_powershell_profile_location`. This todo was found in a stray top-level `todos/` folder
(gitignored by a blanket `*` rule in `.gitignore`, so it never surfaced in `git status` and was
never migrated into the `.claude/todos/` contract) - filed here and moved directly to `done/`
since the work already shipped and is memory-documented.

## Acceptance

- `claude-fibo-mid` starts a session authed as Fibo at the mid tier; `claude-heavy` still starts
  personal at heavy; both run at once in separate terminals without clobbering each other's login.
  Confirmed via the profile function existing and being invoked for `fibo`.
