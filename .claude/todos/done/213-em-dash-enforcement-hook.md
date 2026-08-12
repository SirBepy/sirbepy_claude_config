<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforcement hook for the "never use em dash" rule

**Type:** skill-improvement

## Goal

Claude broke the global CLAUDE.md rule "Never use the em dash character anywhere, ever. Use a
comma, colon, or hyphen instead" repeatedly within a single session (2026-07-17, at least 5
separate assistant messages while building `skills/mockup/`). A rule that only lives in prose
gets violated under load - it needs a mechanical gate, same lesson as todo 08 (chained shell
commands) which hit the identical enforcement-gap pattern for a different rule.

## Context

The rule lives in `CLAUDE.md` ("Communication" section). Hooks are configured via
`settings.json` (`update-config` skill knows the mechanics; global hooks dir is
`~/.claude/hooks/` - see `gh-account-switch.sh` for an existing PreToolUse example, and todo 08
for a sibling proposal targeting shell-command chaining).

Nuance: there's no PreToolUse/PostToolUse hook stage that inspects the assistant's own free-text
response content - hooks fire on tool calls, not on prose tokens. The closest mechanical gate is
a `Stop` hook (fires when Claude finishes responding) that can read the just-completed
assistant message from the transcript and check it for the em-dash character (`â€”`, U+2014).
Whether a `Stop` hook can block/reject completion and force a rewrite, versus only warn
after the fact, needs verifying against what the harness's hook system actually supports before
committing to a design.

## Approach

1. Confirm what hook stage (if any) can inspect/gate the assistant's final text output for this
   session's harness. If none can hard-block, fall back to a warn-only Stop hook that flags
   violations for the dev to notice, rather than inventing a gate that doesn't exist.
2. If a blocking gate is feasible: implement it to scan the outgoing message for `â€”` and reject
   with a message quoting the rule, forcing a rewrite before the turn completes.
3. If only warn-only is feasible: have the hook log/print a flag so violations are at least
   visible per-turn instead of silently accumulating across a whole session before anyone notices.

## Acceptance

- A response containing an em dash either gets blocked and rewritten, or is flagged visibly at
  the time it happens - not just discovered retroactively during a `/close` retrospective.
- Legitimate uses (e.g. quoting external text that itself contains an em dash) aren't silently
  mangled by an overly blunt find-and-replace; a detection-and-flag approach is safer than
  auto-stripping.

## Notes

Same enforcement-gap shape as todo 08 (chained shell commands): a rule stated once in CLAUDE.md,
violated repeatedly under normal working conditions, no mechanical backstop. Worth considering
whether both todos should share one general "CLAUDE.md rule -> Stop-hook lint" mechanism instead
of two bespoke hooks, once todo 08's scope question is answered.
- Dropped via /cleanup-todos 2026-08-11: same verdict as 59 - em dash is a style rule, not a hook-worthy one. Confirmed by dev 2026-08-11.
