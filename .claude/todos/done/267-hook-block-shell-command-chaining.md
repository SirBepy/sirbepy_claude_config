# Enforce the no-shell-chaining rule with a PreToolUse hook

**Type:** skill-improvement

## Goal

Mechanically block `;` / `&&` / `|` command chaining in PowerShell/Bash tool calls instead of relying on Claude remembering the global rule.

## Context

Global CLAUDE.md rule: "Never chain commands with `&&`, `;`, or `|` - one command per call." In the 2026-07-10 settings-rewrite session Claude violated it twice with `;` (self-caught both times, no harm). A rule that gets broken by the model twice in one session under load is an enforcement gap, not a diligence problem - same reasoning as the existing gh-account-switch hook.

**Recurred again 2026-07-29** (todo 421/423 session): repeated `&&`-chained Bash calls, including
`cd <repo> && git <cmd>` (also a distinct violation of the /commit skill's own "use git -C, never
cd before git" rule) and multi-step claim-file writes (`mkdir -p ... && printf ... && mv ...`).
Third recorded instance now - see feedback_cd_and_chaining_in_bash_calls memory.

## Approach

- Add a global `PreToolUse` hook (`~/.claude/hooks/`, wired in `~/.claude/settings.json` next to gh-account-switch.sh) matching Bash + PowerShell tool calls.
- Reject when the command contains a top-level `;`, `&&`, `||`, or `|` OUTSIDE quotes/here-strings. Parsing pitfalls to handle: `;` inside single/double-quoted strings and here-strings is legal (git commit messages), `|` inside quoted args, PowerShell pipelines that are genuinely one logical command (`Get-ChildItem | Select-Object` is currently used constantly and is arguably fine - decide with Joe whether `|` stays allowed and only `;`/`&&` get blocked; recommend blocking only `;` and `&&`/`||` to start).
- Hook output message should remind: "one command per call, use git -C / -Filter instead".

## Acceptance

- A test call with `foo; bar` is rejected with the reminder; `git commit -m "a; b"` passes.
- Existing single-pipeline PowerShell calls keep working (if `|` is exempted).
- Rule violation count drops to zero in subsequent sessions.

## Notes

- Relocated from the claude_usage_in_taskbar backlog (was todo #207) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
- Dropped via /cleanup-todos 2026-08-12: asks to re-implement the never-chain-shell-commands rule that commit b28c296 deliberately RETIRED on 2026-08-11, one day before this was filed. Also duplicates archived 07, 21, 64, 79 and 208. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
