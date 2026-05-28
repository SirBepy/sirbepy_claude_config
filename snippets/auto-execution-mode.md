# Auto execution-mode policy

Projects that `@import` this snippet opt out of the "Subagent-Driven vs Inline Execution" question. Don't ask me which mode to use - decide and proceed.

## What this overrides

Normally, before executing a ready plan, you'd surface inline-vs-subagent-driven as a choice. With this snippet imported, skip that question entirely.

## How to decide instead

Apply my global "Subagent-Driven vs Inline Execution" rule yourself and act on its output without confirming:

- Inline (default): small features, fewer than 4 tasks, fewer than 3 files, tightly sequential. Just do it.
- Subagent-driven: 5+ independent tasks across multiple files where fresh context per task earns its keep.

When it's a genuine coin-flip, pick inline and say one line why before starting. Don't stop to ask.

## What this does NOT change

- Plan quality (brainstorming/planning rigor untouched).
- Destructive/irreversible steps still require explicit confirmation regardless of mode.
- Subagents stage-only and never commit; main agent runs /commit.
