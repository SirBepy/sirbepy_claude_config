<!-- Claim before executing: .claude/todos/.claims/ per .claude/skills/close/ai-todos-format.md -->
# iterate-it: a multi-topic ask means one thread per topic

**Type:** skill-improvement
**Origin:** ai (dashboard-a tech stack chat, 2026-10-21)

## Problem

Joe answered a question card with "/iterate-it this" on two separate questions (Gmail push vs pull, long-running vs
serverless) and asked about Rust and tenancy in the same batch. Claude ran ONE combined iterate-it over all four topics
because they depend on each other. Joe: "did you only really do one /iterate-it combined ... typescript vs rust was
meant to be one thread". The combined run (~320k subagent tokens) gave Rust one round of attention; the four threads
had to be re-run separately (~1.2M tokens more). The skill has no rule for multi-topic invocations.

A second, related gap: Claude's own reviewer briefs carried a "two people, one month" deadline from an inherited
brief and told polish rounds to "cut v1 bloat"; Joe's bar was long-term ("we are looking for the best things long
term"), so a third pass was needed. Vault note: `Working with Claude - preferences.md` (2026-10-21 bullets).

## Approach

Edit `C:\Users\tecno\.claude\skills\iterate-it\SKILL.md`:
1. Add a rule: when the dev names several topics (or several question-card answers each say "iterate-it this"), run
   one thread per topic, in parallel (each thread still one sub per round, sequential within the thread). Shared
   context goes into each thread's CONTEXT block; cross-topic dependencies are noted, not merged. Only combine when the
   dev asks for one combined run.
2. Add to the per-round flow: the brief states the dev's own success bar (long-term vs short-term) and never adds a
   deadline or "cut bloat" instruction the dev did not set.

## Acceptance

SKILL.md has both rules; a dry read of the "Arguments"/"Algorithm" sections makes the multi-topic case unambiguous.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): iterate-it has a Multiple topics section (one parallel thread per topic, one sub per round within a thread, combine only on request) and per-round step 1 states the dev's own success bar with no invented deadline or cut-bloat instruction.
