<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `/respawn` still does spawn_chat-then-close_session; a single `respawn` tool now replaces both

**Type:** skill-improvement
**Origin:** ai

## Goal

Point `~/.claude/skills/respawn/SKILL.md` at the new `respawn` MCP tool, and delete the ordering
rule and the failure modes that only existed because the skill had to sequence two calls.

## Context

Filed 2026-08-22 from the `claude_usage_in_taskbar` repo, which is where the tool was added. The
skill lives in the global tree, so it was deliberately NOT edited from that session.

Claude Conductor now ships a `respawn` MCP tool alongside `spawn_chat`. It does both halves in one
call: spawns the successor, records `successor_of` on it, and flags the caller for close (its own
pump tears it down at turn end). The app follows the link, so the user's pane, sidebar selection
and composer draft move onto the successor by themselves - the chat visibly continues in the same
window even though the transcript starts empty.

What that makes obsolete in the current SKILL.md:

- **"Hard ordering rule"** (spawn FIRST, close second, because close kills the process that would
  make the spawn call). One tool call, so there is no ordering left to get wrong.
- **Phase 6** - "run `/close`'s Phase 6: `close_session` first, the rename/kill script second". The
  `close_session` half is now done by the `respawn` call itself. The rename/kill script still needs
  to run.
- The **"Requires the `spawn_chat` MCP tool"** precondition becomes `respawn`.
- Phase 5's two refusal cases (foreign cwd, second spawn in a turn) still apply verbatim - same
  guards, same method underneath.

`spawn_chat`'s own tool description was rewritten at the same time: it no longer presents itself as
"the /respawn helper" but as "start a chat that runs ALONGSIDE this one". The skill should not
mention it any more except to say it is the other thing.

## Approach

1. Read `~/.claude/skills/respawn/SKILL.md` in full.
2. Replace the `spawn_chat` precondition with `respawn`.
3. Delete the "Hard ordering rule" section outright.
4. Rewrite Phase 5 as one `respawn` call, keeping the cwd/one-per-turn refusal guidance and the
   `{ok: false}` -> stop-and-report rule (still correct: a failed respawn leaves the chat open,
   since nothing was closed).
5. Rewrite Phase 6 down to "tell Joe the successor's id, then run the rename/kill script" - drop
   the `close_session` call and the ordering sentence that justified it.

## Acceptance

- The skill never mentions `close_session` or `spawn_chat` as part of its own flow.
- A `/respawn` run makes exactly one lifecycle tool call.
- The `{ok: false}` stop-and-report rule survives.

## Notes

Related, in the app repo not this one: `.claude/todos/684-live-verify-respawn-end-to-end.md` is the
end-to-end verification todo. It describes the OLD two-call flow, so it needs the same update; that
one belongs to whoever picks it up over there, not to this todo.
