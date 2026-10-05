<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# A Claude-volunteered token-cost figure skips the caching/deferral check

**Type:** skill-improvement
**Origin:** ai

## Goal

Make sure that before Claude states a token count as a per-turn COST (a bill, a "costs N tokens
every turn" framing), it has checked whether that content is prompt-cached or deferred. Today
nothing fires in that situation when Claude raises the number itself rather than being asked.

## Context

Incident, 2026-09-28, claude_usage_in_taskbar session `7099dea0`. Designing a new MCP tool, Claude
measured the existing tool schemas by character count (~23,100 chars, "~5,780 tokens") and
presented that as a per-turn bill across TWO consecutive question cards, then shaped a design
recommendation around avoiding it ("fold the params into `spawn_chat` to save ~200 tokens/turn").
The dev pushed back ("is there a better way to myb make it so its not 5780 tokens every turn?")
and only then did Claude load the `claude-api` skill and check. The figure was wrong as a bill by
roughly an order of magnitude, for two independent reasons:

1. The harness already defers those MCP tool schemas behind `ToolSearch` (observable in the same
   session: `mcp__cc_conductor__send_message` appeared only as a name and had to be fetched).
2. What is not deferred sits in the `tools` block, which renders first and is byte-identical per
   session, so it is a cache read at ~0.1x from turn 2 on.

The `claude-api` skill's own trigger text covers this ("the user asks about an LLM
(pricing/model choice/limits/caching) - never answer from memory"), but it is phrased around the
USER asking. A number Claude volunteers mid-design never reads as a user question, so the trigger
does not fire. Two question cards were spent on a false premise that one tool call would have
removed.

**Important for whoever fixes this:** `claude-api` is a BUNDLED Claude Code skill (it extracts to
`AppData/Local/Temp/claude/bundled-skills/<version>/...`), not one of the dev's own skills under
`~/.claude/skills/`. Its description cannot be edited durably. The fix has to live somewhere the
dev owns.

The project-local version of the lesson is already recorded in claude_usage_in_taskbar's memory
(`project_mcp_tool_def_per_turn_cost`, updated 2026-09-28) and in that repo's
`docs/mcp-surface-decision.md`. This todo is about the cross-project rule.

## Approach

Pick one, in order of preference:

1. **One line in global `CLAUDE.md`'s Execution Discipline section**, next to the existing
   "Before asserting X does/causes Y because Z" rule, which is the same failure shape: "Before
   presenting any token count as a per-turn or per-request COST, check whether it is cached or
   deferred - a raw character count is a context-footprint figure, not a bill." It extends a rule
   that already exists rather than adding a new surface.
2. A `PreToolUse` hook on the question tool that flags a card whose body contains a token-cost
   figure. Heavier, and likely noisy.

Option 1 is recommended. It costs a sentence, and the existing rule already trains the right
reflex; it just does not name cost claims.

## Acceptance

- The rule exists in a file the dev owns and that loads every session.
- It names the distinction explicitly: context footprint versus billed cost.
