<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforce the "never use em dash" rule with a hook instead of willpower

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop Claude from violating the global CLAUDE.md rule "Never use the em dash character anywhere,
ever. Use a comma, colon, or hyphen instead" - broken repeatedly (dozens of times) in a single
2026-08-08 session in `claude_usage_in_taskbar`, entirely in `send_message` calls, with zero
consequence, because nothing enforces it.

## Context

Per `feedback_em_dash_scope.md` the rule scope is already correctly understood (code + messages,
not just code) - this isn't a knowledge gap, it's a generation-time slip under normal sentence
flow. The em dash is an easy character for the model to reach for structurally (parenthetical
asides, clause breaks) and self-monitoring during generation doesn't reliably catch it, the same
failure shape as `.claude/todos/21-enforce-no-chained-shell-commands.md` and
`.claude/todos/89-block-bash-backend-writes-hook.md` - both existing "hook > willpower" precedents
for a rule that's clearly stated but not mechanically checked.

Concrete incident: 2026-08-08, `claude_usage_in_taskbar` session investigating AUQ chip
rendering - roughly 15+ `send_message` calls in one session each containing at least one literal
"â€”" (U+2014) character, despite the rule being active in that project's inherited global
CLAUDE.md the entire time.

## Approach

A `PreToolUse` hook (see `~/.claude/hooks/` for the existing pattern, e.g.
`gh-account-switch.sh`) on `send_message` (and any other user-facing text tool - check
`mcp__cc_conductor__post_message` too) that scans the outgoing `text` param for U+2014 and either:
- blocks with a message naming the rule and asking for a rewrite, or
- auto-substitutes " - " / ", " and lets the call through (softer, but risks silently changing
  intended punctuation/meaning - probably worse than blocking).

Start as warn-only (log hits, don't block) for a few sessions to confirm the detection doesn't
false-positive on anything, then flip to block, mirroring todo 21's prototype-first approach.

Scope question: is this specific to `claude_usage_in_taskbar` (its own `mcp__cc_conductor__*`
tools) or should it generalize to ANY tool call carrying user-facing text across all projects?
The rule itself is global (`~/.claude-personal/CLAUDE.md`), so probably the latter, but the tool
names to hook differ per project (not every project has `send_message`) - may need to hook on
tool-name pattern (`*send_message*`, `*post_message*`) rather than an exact list.

## Acceptance

- A `send_message`/`post_message` call whose text contains U+2014 gets flagged/blocked with a
  message naming the rule.
- A call with a plain hyphen, en dash, or no dash-like character at all passes through untouched.
- Verify empirically with a live no-op test before considering this done, per
  [[verify-shared-mechanism-scope-empirically]].

## Notes

- Dropped via /cleanup-todos 2026-08-11: cosmetic rule with zero functional consequence; a per-project tool-name matcher is real maintenance surface. Confirmed by dev 2026-08-11.
