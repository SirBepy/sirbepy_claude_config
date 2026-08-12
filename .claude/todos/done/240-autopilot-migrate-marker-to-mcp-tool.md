<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=3, reconfirm-count=1, content-hash=eeffaab7 -->
# autopilot: migrate the cc-autopilot text marker to an MCP tool call

**Type:** skill-improvement

## Goal

`skills/autopilot/SKILL.md` currently signals its sidebar badge state via a stripped
text marker in the model's own response (`<cc-autopilot:on>` / `<cc-autopilot:off>`).
Migrate this to a proper MCP tool call instead of a magic text token the app has to
parse and strip out of rendered chat.

## Context

`skills/autopilot/SKILL.md` (as of 2026-08-01), "Sidebar badge" section, lines 13-19:

```
## Sidebar badge

Emit `<cc-autopilot:on>` at the end of your **first response** after activating autopilot.
The app reads this marker and shows an "autopilot" badge on the session row in the
sidebar so Joe knows the session is running unattended.

Emit `<cc-autopilot:off>` at the end of your **final response** when the run is fully
complete (after the written summary). The badge disappears.

These markers are stripped from the rendered chat - Joe never sees them as text.
```

This is a text-based side channel: the app has to scan every assistant response for this
literal string, strip it before rendering, and interpret its presence as a state change.
It works but is fragile (any accidental stray mention of the literal string in a
different context could misfire the badge) and inconsistent with how this codebase does
proper machine-to-machine signaling elsewhere via actual MCP tools.

**This migration is explicitly BLOCKED** on two existing todos in a DIFFERENT project's
own todo backlog - `claude_usage_in_taskbar` (the Tauri app referenced elsewhere in this
codebase, e.g. `skills/character-creator/SKILL.md`'s description: "Scaffold character
bundles for my claude_usage_in_taskbar Tauri app"). The blocking todos are **id 435** and
**id 426** in that project's own `.claude/todos/` backlog (NOT this repo's backlog - this
repo is `~/.claude`, the skills/config repo; `claude_usage_in_taskbar` is Joe's separate
Tauri desktop app project where the sidebar/badge UI itself lives). This todo cannot be
completed independently of that project's work landing first - whatever MCP tool surface
those two todos build is presumably the mechanism this skill needs to call into.

## Approach

1. **Do not start implementation here without first checking
   `claude_usage_in_taskbar`'s own `.claude/todos/435-*.md` and `.claude/todos/done/435-*.md`
   (and the same for 426)** to see whether they've landed and what MCP tool surface (if
   any) they exposed for session-state signaling. If neither has landed yet, this todo
   stays blocked - do not invent a placeholder mechanism, since it would likely conflict
   with whatever those todos actually build.
2. Once unblocked, replace the two text-marker emission points in
   `skills/autopilot/SKILL.md` (Sidebar badge section, and the "Order of operations"
   step-1 cross-reference: "END THIS FIRST RESPONSE WITH `<cc-autopilot:on>`") with calls
   to the new MCP tool (exact tool name/schema determined by whatever 435/426 produced).
3. Update the "these markers are stripped from rendered chat" line to describe the new
   mechanism instead (an MCP tool call doesn't need chat-stripping - it's a distinct
   message type already, unlike an inline text token).
4. Grep this repo (`~/.claude`) for any OTHER reference to `<cc-autopilot:on>` or
   `<cc-autopilot:off>` (e.g. in `refs/`, other skills that might reference autopilot's
   badge behavior) and update those too.

## Acceptance

- `claude_usage_in_taskbar` todos 435 and 426 are confirmed landed (moved to `done/` in
  that project, or otherwise verifiably complete) before any code in THIS repo changes.
- `skills/autopilot/SKILL.md` no longer instructs emitting the literal
  `<cc-autopilot:on>`/`<cc-autopilot:off>` text tokens - it calls the new MCP tool
  instead, at the same two trigger points (first response after activation, final
  response on completion).
- A real `/autopilot` run confirms the sidebar badge still appears/disappears correctly
  end to end using the new mechanism.

## Notes

This todo lives in `~/.claude`'s backlog (the skill being changed lives here) but its
blocker lives in a different project's backlog entirely - a genuinely cross-project
dependency. Do not attempt to "solve it locally" by re-deriving what 435/426 were
supposed to build; go read them.
- Dropped via /cleanup-todos 2026-08-12: scored 3/10 - blocked on an unverified external dependency by its own text, with no misfire behind it. Architecture preference, not a defect. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
