<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforcement hook for the "never chain shell commands" rule

**Type:** skill-improvement

## Goal

Claude broke the global CLAUDE.md rule "Never chain commands with `&&`, `;`, or `|` - one
command per call" twice in one session (2026-07-15: a `New-Item ... | Out-Null; Move-Item ...`
and a `Remove-Item; ...` compound). A rule that only lives in prose gets violated under load -
it needs a mechanical gate.

## Context

The global rules live in `CLAUDE.md` ("Shell Commands" section). Hooks are configured via
settings.json (`update-config` skill knows the mechanics; global hooks dir is
`~/.claude/hooks/` - see `gh-account-switch.sh` for an existing PreToolUse example).
Nuance: legitimate uses exist - `|` piping INSIDE one logical command is allowed by Joe's rule
intent? No: the rule bans `|` too, but existing skills DO use pipes (e.g.
`Get-ChildItem | Remove-Item` in close's screenshot cleanup, and the process-hygiene check).
So the enforcement can't be a dumb regex on `;|&&|\|` - scope needs deciding with Joe first.

## Approach

1. Ask Joe the scope: block only `;` and `&&` chaining (clearly two commands)? Warn-only vs
   hard-block? PowerShell tool only, or Bash too?
2. Implement as a PreToolUse hook on the PowerShell/Bash tools per `update-config` mechanics,
   returning a deny with a message quoting the rule when the pattern matches.
3. Whitelist known-good skill invocations if needed (e.g. pipes into `Out-Null`,
   `Measure-Object` one-liners) per Joe's call in step 1.

## Acceptance

- A deliberately chained `foo; bar` PowerShell call gets blocked (or warned, per chosen scope)
  with a message naming the rule.
- Existing skills' legitimate pipe usage still runs without prompts.

## Notes

Recurred again 2026-07-30, this time in the **Bash** tool (not PowerShell) during a `/commit`
hunk-split: `git apply --cached --recount ... && git diff --cached --stat`, `git diff ... > file
&& cat file`, and `awk ... > file && cat -A ... | head -20`. Confirms the gap is cross-tool, not
PowerShell-specific - any enforcement hook needs to cover both the PowerShell and Bash tool
call sites.

Also recurred 2026-07-20 in `server_supervisor` during a `/pickup` + `/autopilot` + `/commit`
session: claim-file creation (`PID=$$ && ISO=... && printf ... && mv -n ...`), a
todo-move-and-claim-release (`mkdir -p ... && mv ... && rm -f ...`), and several `cd <path> &&
<cmd>` combos for cargo/npm. None were caught until a retrospective `/close` review. That repo
had filed its own duplicate of this todo (`server_supervisor/.claude/todos/0011-...`); it was
archived on 2026-07-30 in favour of this file, since the hook belongs in global `~/.claude/hooks/`
and the project backlog is the wrong home for it. Its one extra design note: the hook must not
false-positive on `&&`/`;`/`|` appearing inside quoted arguments, e.g. a multi-line commit message
body or a regex pattern.
- Duplicate of 07 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
