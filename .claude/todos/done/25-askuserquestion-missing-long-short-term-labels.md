<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=57367953 -->
# AskUserQuestion calls skipped long-term/short-term-best labeling on a tagged question

**Type:** skill-improvement
**Origin:** ai

## Goal

Catch (and stop repeating) a gap between the global CLAUDE.md's `AskUserQuestion`
formatting rule and what actually got produced in a live session.

## Context

Global `~/.claude-fibo/CLAUDE.md` ("Communication" section) requires: every question
uses `AskUserQuestion` with a domain tag (`[UX]`/`[ARCH]`/`[SEC]`/`[DATA]`/`[TOOLING]`),
and â€” except for `[UX]` â€” the long-term-best and short-term-best pick must be marked
**inside the option label/description itself**, not just in surrounding chat prose.

During the 2026-07-27 `/pickup` session on todo 140 (Storybook setup), a concurrent-edit
anomaly was found mid-task and surfaced via `AskUserQuestion` tagged `[SEC]` (see that
session's transcript). The question correctly used the domain tag and a two-option
shape with one option marked "(Recommended)", but neither option's label/description
called out which pick was long-term-best vs short-term-best â€” the rule was only
partially applied. This wasn't a case where "no clear winner" applied (a tradeoff could
have been named: e.g. "resolve now" is short-term-safer, "investigate first" is more
correct long-term if concurrent state is actually unexpected).

Not a one-off wording nitpick â€” the rule exists so Joe can skim options without reading
surrounding commentary, per the same CLAUDE.md section. Worth checking whether this is a
recurring miss (search past session transcripts/memory for other `AskUserQuestion` calls
tagged `[ARCH]`/`[SEC]`/`[DATA]`/`[TOOLING]` missing the long/short-term labels) or a
single lapse.

## Approach

- Audit recent `AskUserQuestion` invocations (this session + a few prior ones if
  accessible) for the same gap.
- If it's recurring: this may warrant a lightweight self-check step before calling
  `AskUserQuestion` with a non-`[UX]` tag â€” e.g. a mental checklist "did I name the
  long-term and short-term pick in each option's label/description, not just in my
  prose?" No new skill file needed; this is an existing global-CLAUDE.md rule that
  needs better adherence, not a new rule.
- If it's a one-off: no action needed beyond this record existing as a reminder.

## Acceptance

- Confirms whether this is a pattern or a one-off.
- If a pattern: some concrete adherence improvement identified (even just "reread this
  rule before crafting question options" is enough â€” this doesn't need new tooling).

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 149; renumbered to 25 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: grep `~/.claude/projects/**/*.jsonl` for `AskUserQuestion` calls tagged `[ARCH]`,
  `[SEC]`, `[DATA]` or `[TOOLING]` and check whether each option's label or description actually
  carried a long-term or short-term call-out. If it is a recurring miss, add one line to CLAUDE.md's
  existing rule; if a one-off, close the todo. The "audit not yet run" blocker is unexecuted work,
  not a decision anyone owes. This was produced by a strict second-pass re-triage that specifically
  asked whether a defensible answer exists without the dev; it concluded yes. Not executed only
  because the session ended.
- **Further evidence (2026-08-08, windows_taskbar_widgets session).** Both `AskUserQuestion` calls
  this session (4 questions total, tags implied `[ARCH]`) omitted the domain-tag text prefix
  entirely, not just the long/short-term labels â€” a more complete instance of the same drift.
  Strengthens the case that this is recurring, not a one-off.
- Dropped via /cleanup-todos 2026-08-11: audits adherence to a rule already known; 2 data points, and reread-the-rule is not a mechanism. Confirmed by dev 2026-08-11.
