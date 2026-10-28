<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Problem: Claude narrates before tool calls

**Type:** skill-improvement

## Goal

Stop Claude from writing a sentence (or half-sentence ending in a colon) immediately before a
tool call, which the "work quietly" rule already forbids but which still happens under load.

## Context

Example from a past session: "Good, no cycle. Let me build to verify:" - that text appears as a
standalone bubble in the app, looks unfinished, and violates the "minimize narration between tool
calls" rule.

What's already in place: `~/.claude/CLAUDE.md` under Communication: "Work quietly: minimize
narration between tool calls. No play-by-play ("Now let me...", "Let me check..."). Batch
independent tool calls, let results speak, and give ONE tight summary at the end."

Why it still happens: CLAUDE.md is injected as **context** (late in the prompt), not as a system
prompt. The model treats context-layer instructions with lower authority than system-prompt-layer
instructions, especially when the context window grows long and those instructions get pushed far
back. Same root cause as [[11-auto-commit-enforcement-hook]] - rules living only in context/memory
get deprioritized as the window fills.

Verified 2026-07-17: `~/.claude/settings.json` has no `systemPrompt` field yet - this is still
unimplemented, not stale.

## Approach

Candidate fix: add a `systemPrompt` field to `~/.claude/settings.json`. Content there lands in the
actual system prompt layer - higher model authority than CLAUDE.md. Proposed value:

```
No text before tool calls ever. No "Let me...", "Now I will...", "Good, ...". No dangling colons
before a tool. Batch independent calls silently. One tight summary after all tool results are in.
```

Open question (needs a decision before implementing, not Claude's to pick alone): is
`settings.json`'s `systemPrompt` field the right lever here, or is there a better mechanism (e.g.
a `PreToolUse` hook that blocks/warns on narration text, tweaking the CLAUDE.md wording instead,
something else)? The `update-config` skill owns `settings.json` changes - route implementation
through it once the lever is chosen.

## Acceptance

- Claude no longer emits a standalone narration sentence/fragment immediately before a tool call,
  across long and topic-mixed sessions (not just short ones where the instruction is still fresh
  in context).

## Notes

Filed 2026-07-17 from a stray top-level `todos/` folder that predated (and was never migrated
into) the `.claude/todos/` contract - see [[10-multi-account-cli-wrappers]] for the root-cause
explanation (blanket `*` `.gitignore` rule hid the folder from `git status`, so no `/close`
migration pass ever saw it).
- Dropped via /cleanup-todos 2026-08-11: cosmetic, and the proposed systemPrompt fix is unverified speculation. Confirmed by dev 2026-08-11.
