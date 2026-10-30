<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 4; pc-1254/pc-1255 cover single Conductor lines, pc-0424 rejected path-scoped rules -->
# Trim global CLAUDE.md: move or cut about 1,500 of its 3,959 words

**Type:** task
**Origin:** dev
**Summary:** The global rules file every session loads gets much shorter and regains CI headroom, with no rule lost.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. CLAUDE.md wording is the dev's call, so it was not edited unattended.

## Goal

CLAUDE.md holds only rules that must be in every session's context, each stated once, with room under the CI budget for new rules.

## Context

- `python ci/check_instruction_budget.py --root .` on 2026-10-30: "PASS: CLAUDE.md is 6534 tokens, ceiling is 6558, headroom 24". 3,959 words, 154 lines. Anthropic's memory docs say to target under 200 lines and that `@import` does not reduce load.
- The rules-slice auditor's section table sums to ~1,577 cuttable/movable words (40%): prose re-explaining hook-enforced rules (gh account switch, shell write ban, commit window, dev servers, push gate), incident dates and todo ids despite `refs/incidents.md`, Conductor-only rules loaded in every session, rules duplicated in refs. The refuter sampled three sections: the gh section is mostly cuttable; the shell-write ban is partly load-bearing because its hook fails open; the MEMORY.md index-size warning exists nowhere else, so it must move, not be cut.
- `CLAUDE.md:150` says the Agent tool takes no `effort` parameter (checked 2026-09-10). False since Claude Code 2.1.292; `refs/delegation-doctrine.md` and `skills/autopilot/SKILL.md` were already corrected on 2026-10-30.
- `CLAUDE.md:59` supervisor fallback contradicts `hooks/dev-server-guard.py` (see pc-1278).
- Path-scoped `~/.claude/rules/` was rejected in done todo pc-0424 (2026-08-22). One of its reasons is obsolete: 2.1.288 now loads rules on Write/Edit. Worth re-asking, not auto-adopting.
- The "@import" snippets (`terse-replies.md`, `auto-commit.md`) are read-once instructions, ~1,900 words; auto-commit's ~1,000-word fold section is a rare path.

## Approach

1. Draft a section-by-section cut list (keep / cut / move to ref / now hook-enforced) and show it to the dev before editing.
2. Apply the accepted cuts; fix line 150 and line 59 in the same pass.
3. Re-run the budget check and record the new headroom.

## Acceptance

- The dev approved the cut list.
- `ci/check_instruction_budget.py` passes with at least ~1,000 tokens of headroom.
- No rule disappears without a home (a ref, a hook, or an explicit dev decision to drop it).
