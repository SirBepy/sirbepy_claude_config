<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=7, reconfirm-count=1, content-hash=7ffd74ba -->
# /create-pr's preview card can never render under the Conductor turn-status rule

**Type:** bug
**Origin:** ai

## Goal

Make `/create-pr` step 4's PR preview card actually appear in Claude Conductor,
or document the real mechanism if the marker route is dead there.

## Context

Observed 2026-08-18 in the `revaire-mobile` Conductor session on PR #964.
Joe: *"i dont see the preview card"*.

Two rules collide, and the collision is unconditional, not a one-off slip:

1. `~/.claude/skills/create-pr/SKILL.md` step 4 requires the three
   `<cc-pr-title:>` / `<cc-pr-body:>` / `<cc-pr-commits:>` markers to be emitted
   as **plain assistant text**, and states *"Step 4 must be the FINAL action of
   its turn - no tool call after it."*
2. The Conductor session prompt requires `report_turn_status` to be called **as
   the very last thing every turn**, and a Stop hook blocks the turn from ending
   until it is.

So a tool call always lands after the markers. There is no ordering that
satisfies both.

A second, possibly fatal problem in the same environment: that same session
prompt says *"Your assistant text and tool-call narration are never rendered in
the chat view at all"* and that only `send_message` bubbles reach the user. If
the app parser reads the raw assistant text before display, markers still work;
if it only parses what `send_message` emits, the marker route cannot work in
Conductor at all and the skill needs a Conductor-specific path.

## Approach

Determine which of the two is true first - whether the Conductor parser reads
raw assistant text or only `send_message` payloads. That single fact decides the
fix:

- Parser reads assistant text: relax step 4's "no tool call after it" to exempt
  `report_turn_status`, since that call is mandated by the harness and carries no
  user-visible text.
- Parser only reads `send_message`: add a Conductor branch to step 4 that emits
  the markers through `send_message` instead, and say so explicitly in SKILL.md.

Either way, note in SKILL.md that the rendered-inline body and the card are
redundant - emitting both produced a duplicate wall of text in this session.

## Acceptance

Running `/create-pr` in a Conductor session shows the PR preview card, and the
body is not also duplicated as a plain chat bubble.
