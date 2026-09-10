<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=00a5a25b -->
<!-- duplicate-checked 2026-09-05: grepped backlog + done/ for "respawn". done/480 and done/497 are about the respawn skill's own MCP tool plumbing; live 491/938/939/948 matched only incidentally. Nothing covers Claude REACHING for respawn in the first place. -->
# No rule points Claude at /respawn when a session restart is needed

**Type:** skill-improvement
**Origin:** dev

## Goal

When Claude concludes that a Claude Code restart is required, it should tell Joe to run
`/respawn` rather than telling him to restart the app. Today nothing in the global ruleset
says this, so Claude defaults to "restart Claude Code" and Joe has to correct it.

## Context

2026-09-05, head_soccer_v_fable_oneshot session. Claude committed a new project-scoped
`.mcp.json` registering the Roblox Studio MCP server, then told Joe: "Restart Claude Code to
load it." Joe replied: "when you need a restart, just /respawn".

`~/.claude/skills/respawn/SKILL.md` carries `disable-model-invocation: true`, so Claude can
never fire it itself. That is deliberate and should stay: respawn closes the chat, which is
Joe's call. The gap is that Claude has no instruction to SUGGEST it, so the skill sits unused
in exactly the situation it was built for.

Restart-needed situations Claude actually hits: a settings.json change that the harness reads at
boot, and a newly installed skill or hook.

**A new or changed MCP server entry is NOT one of them, contrary to what this todo said when it
was filed.** In Conductor no restart of any kind loads a non-conductor MCP server, ever. See the
"MCP is a special case" section below and todo 955.

## Approach

Add one bullet to `~/.claude/CLAUDE.md` under Communication, alongside the popup-attribution
bullet it sits closest to in spirit. Wording along the lines of:

> When a change only takes effect after a Claude Code restart (settings.json, a new skill or
> hook), never tell Joe to restart the app. Tell him to run `/respawn`, which hands this chat's
> context to a fresh session in place.

The original draft listed "new MCP server" first in that parenthesis. Do not reinstate it; see
below.

Rejected: putting this in `skills/respawn/SKILL.md` itself. That file is only read once Joe has
already typed `/respawn`, so a rule living there can never fire at the moment Claude is about to
say "restart the app". It has to be in an always-loaded surface.

## MCP is a special case - question ANSWERED 2026-09-05

This todo asked whether `/respawn` genuinely picks up a new `.mcp.json`. **It does not, and
neither does a full app restart.** Verified the same day, two respawns into the attempt:

Conductor passes `--strict-mcp-config` alongside `--mcp-config` at
`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\src-tauri\src\daemon\lifecycle\spawn.rs:121`,
which makes the generated per-session config the exclusive MCP source. That file contains only
`cc_conductor`. Project `.mcp.json`, project `.claude/settings.json` and machine-local
`.claude.json` are all ignored. Deliberate, added 2026-09-03 in commit `1ac56b80` for Conductor's
own todo 867.

The half of the original reasoning that was right: respawn IS a genuinely new CLI process that
re-reads config at startup. The half that was wrong: what it re-reads is Conductor's file, not
the repo's.

So the carve-out this todo anticipated is needed, but the instruction inside it is not "a real app
restart" as guessed - it is that **there is no restart gesture that works at all**. Full receipts
and the Conductor-side options in todo 955.

## Acceptance

- `~/.claude/CLAUDE.md` contains the rule, and the always-loaded token budget check in
  `ci/run_all.py` still passes.
- The rule's examples do not list MCP servers as restart-fixable.
- Coordinated with 955 so the two do not each add their own always-loaded bullet; one bullet
  covering both is the cheaper shape given the zero-headroom token ceiling.

## Notes

Joe's exact words, so the intent is not paraphrased away: "when you need a restart, just
/respawn".
- DONE 2026-09-10 via /loop-todos cycle 1. CLAUDE.md line 22, in Communication next to the popup-attribution bullet as this todo directed: when a change only takes effect after a Claude Code restart (a settings.json edit, a newly installed skill or hook), never tell Joe to restart the app, tell him to run /respawn, which hands this chat context to a fresh session in place. Verified the gap first rather than trusting the file: grep for respawn in CLAUDE.md returned nothing before the edit and matches the new bullet after. MCP servers are deliberately NOT listed as an example, per this todo rejecting the earlier draft that led with them - MCP config is not restart-fixable in this harness, so naming it would have been wrong. python ci/run_all.py exits 0.
