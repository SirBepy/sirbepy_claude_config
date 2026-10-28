<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=4, reconfirm-count=1, content-hash=fab72e0c -->
# rate-it: drop the never-used --research/--dont-research flags, keep auto-detect + free-text opt-out

**Type:** skill-improvement

## Goal

`skills/rate-it/SKILL.md` documents explicit `--research`/`--dont-research` flags for
overriding its auto-detection of whether a rating needs current web information. Per the
skill audit these flags are never actually used in practice - the auto-detect logic
already covers the real cases well. Drop the flags from the argument grammar and
frontmatter, keep the auto-detect logic as the sole mechanism, and preserve a free-text
opt-out path (the dev saying something like "don't research this, just rate from what
you know" inline) instead of a formal flag syntax.

## Context

`skills/rate-it/SKILL.md` (as of 2026-08-01):

- Frontmatter (line 3-4):
  ```
  description: Triggers on /rate-it only. Brutally honest 1-10 rating with named score
  tiers, no sugar-coating. Solo by default; pass an integer N for an N-subagent panel
  (higher stakes, ~5-6x cost). Auto-detects if web research is needed; supports
  --research and --dont-research flags.
  argument-hint: "[N] <thing to rate> [--research|--dont-research]"
  ```
- "Research" section (lines 79-92):
  ```
  ## Research

  Before rating, decide: does accuracy require current information the model may not have?

  Auto-research triggers: market trends, pricing, tool/library popularity, recent news,
  competitor comparisons, anything that changes frequently.

  Does NOT trigger: general best practices, architecture decisions, code patterns,
  timeless tradeoffs.

  Flag overrides:

  - `--research`: always search first, skip detection
  - `--dont-research`: skip search, rate from existing knowledge only

  In panel mode, the main agent decides whether research is needed and runs it once
  before dispatching subagents. Subagents do not run their own research - they receive
  the research findings as part of their hypothesis prompt.
  ```

This skill's own "Free-form slash command args" convention (per project memory:
"Prefer natural-language token parsing over rigid positional syntax when designing slash
command arguments") argues against a formal `--flag` syntax when free text already
covers the same intent more naturally.

## Approach

1. Read `skills/rate-it/SKILL.md` in full before editing.
2. Update the frontmatter `description` to drop "supports --research and --dont-research
   flags" - keep "Auto-detects if web research is needed."
3. Update `argument-hint` to drop `[--research|--dont-research]`.
4. In the "Research" section, remove the "Flag overrides" subsection entirely. Replace it
   with a free-text opt-out note: if the dev's invocation text explicitly says something
   like "don't research" / "rate from what you know" / "skip the search," honor that as
   an override of auto-detection - same effect as the old `--dont-research` flag, just
   parsed from natural language instead of a token. There is no need for an equivalent
   free-text "force research" override beyond what auto-detect already triggers on,
   UNLESS the dev's text explicitly asks for it (e.g. "look this up before rating") - note
   that as the `--research` equivalent.
5. Grep the rest of this repo for any other reference to `--research`/`--dont-research`
   in the context of `/rate-it` (e.g. `skills/rate-it-and-commit/SKILL.md`, which forwards
   panel-size args to `/rate-it` per its own "Rules" section - confirm it doesn't also
   reference these flags) and update/remove accordingly.

## Acceptance

- `skills/rate-it/SKILL.md`'s frontmatter and argument-hint no longer mention
  `--research`/`--dont-research`.
- The "Research" section documents free-text opt-out/opt-in instead of formal flags,
  while keeping the auto-detect trigger list unchanged (that logic is not being touched,
  only the override mechanism).
- No other file in the repo still documents the old flag syntax for `/rate-it` after the
  grep sweep in step 5.

## Notes

- Dropped via /cleanup-todos 2026-08-12: scored 4/10 - restates the already-established free-form-args convention as if new, resting on an unverifiable never-used claim. Low-payoff style churn. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
