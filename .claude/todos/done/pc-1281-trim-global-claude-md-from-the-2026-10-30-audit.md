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

## Notes

2026-11-07 (/loop-todos, unattended; Joe asked for a full draft to review, nothing from it is applied):

**Draft cut list for Joe's review.** 43 items, total 1,587 tokens saved: `CLAUDE.md` 27,019 chars / 6,755 tokens now
(197 over the 6,558 ceiling) becomes 20,669 chars / 5,168 tokens, i.e. 1,390 tokens of headroom (acceptance asks
~1,000). The list is executable: `.claude/todos/notes/1281-cut-list.py` holds every item's exact start/end anchors
and replacement text, applies them to an in-memory copy of `CLAUDE.md`, asserts each anchor is unique, and prints
this table plus the totals (`python -I .claude/todos/notes/1281-cut-list.py`). Line numbers are CLAUDE.md lines as
of 2026-11-07 after todos 1155, 1270, 1272 and 1296 landed (those already traded their own tokens, so they are
not in this list). Token column = removed chars minus replacement chars, divided by 4.

Disposition per item: **cut** = the text goes, no home needed (illustration, history, restates a neighbour);
**move** = the text already lives in the named ref or must be added there; **condense** = shortened in place and
the full text is already in the named ref or hook. Only items 14 and 36 need new text written into a ref
(14 = new `refs/package-safety.md` holding the resolved-tree advisory paragraph, 36 = the index-size-warning
paragraph into `refs/memory-rubric.md`); every other destination was grepped and already holds the content.

| # | Line | Disposition | Destination | Span cut (start ... end) | Tokens |
| --- | --- | --- | --- | --- | --- |
| 01 | 8 | cut (illustration) | - | "Applies even to tasks that look like mechanical pattern ... or only in one app state?)." | 61 |
| 02 | 9 | cut | incidents.md has the story | "A product-looking question is usually a FE call ... should hold the verdict only." | 56 |
| 03 | 12 | condense | - | "chips there, so hand-written tags on top would be redundant noise." | 14 |
| 04 | 14-18 | 5 tag bullets to 1 | - | "- `[UX]` - visual, layout ... `[TOOLING]` - dev tooling, linting, code style, naming" | 57 |
| 05 | 20 | condense | copy-paste-format.md holds the ruleset | " Core: everything Joe should copy goes in a BLOCKQUOTE ... message length limits." | 78 |
| 06 | 21 | condense | incidents.md (new entry added tonight) | " Not \"usually\", not \"unless the thread is Croatian\". ... (that line governs only the copyable block)." | 58 |
| 07 | 22 | condense | - | "(GitHub/git credential picker, UAC ... Never let Joe wonder who triggered a popup." | 36 |
| 08 | 24 | condense | snippets/terse-replies.md | " No play-by-play (\"Now let me...\" ... decision, blocker, or question." | 29 |
| 09 | 29 | condense | auto-commit.md is the source | " It covers when to commit without asking ... just run `/commit`." | 60 |
| 10 | 30 | condense | builder-preamble.md + dispatch-preamble-guard.py | " Every dispatch prompt MUST include a staging line: ... `refs/process-hygiene.md`." | 86 |
| 11 | 36 | condense | gh-account-switch.sh header | "- A global `PreToolUse` hook (...gh-account-switch.sh) ... already-correct system." | 74 |
| 12 | 41 | condense | shell-content-write-guard.py (fails open, so the rule stays) | " Windows PowerShell 5.1 prepends a UTF-8 BOM ... stay allowed." | 21 |
| 13 | 42 | condense | shell-io-gotchas.md | "- The same encoding layer corrupts the inbound direction too: ... refs/shell-io-gotchas.md`." | 42 |
| 14 | 52 | move | NEW refs/package-safety.md | "- The advisory-DB check must run against the ACTUAL RESOLVED dependency tree ... name-keyed lookup alone." | 66 |
| 15 | 53-54 | merge 2 bullets | - | "- A subagent is required for research ... inline web search." | 8 |
| 16 | 61 | move | process-hygiene.md lines 25-37 | " After running test/build/dev commands, check with `Get-CimInstance ... before claiming done." | 40 |
| 17 | 62 | move | process-hygiene.md lines 42-52 | " turbo `--concurrency=5`; vitest `maxWorkers: 5` ... takes no concurrency flag)." | 58 |
| 18 | 69 | cut | - | " Keep it in the code, not just the commit ... reads the file cold." | 23 |
| 19 | 69 | cut (example) | - | " (`74px rail, 36px avatar, so 7px centres it`)" | 12 |
| 20 | 69 | cut | - | " Same rule in every repo; no numeric cap." | 10 |
| 21 | 80 | cut (admission, not a rule) | - | " Honest limitation: nothing enforces this ... has no mechanical catch." | 39 |
| 22 | 81 | condense | - | " - hedging the noun doesn't hedge a trailing \"so Y happens\" clause ... needs the label." | 16 |
| 23 | 81 | condense | - | " Describing what a skill, command, or third-party artifact will do counts too: ... summaries drift." | 28 |
| 24 | 82 | condense | outbound-verify.md | "Tickets and PRs Claude posts itself are hook-enforced: ... which has no tool call to hook." | 34 |
| 25 | 88 | cut | - | " Not a licence to skip on judgment alone - only an explicit dev instruction does." | 20 |
| 26 | 89 | condense | /commit "Push pipeline" + push-gate.py | "Every commit runs `/test`, every push runs `/code-check` + `/e2e` ... \"Push pipeline\" section." | 26 |
| 27 | 93 | cut whole line | restates line 92 | "- `/test` means the normal (fast) tests; ... Both stay fast-only." | 28 |
| 28 | 97 | condense | - | "Phosphor via CDN (`<script ...`) ... Browse: https://phosphoricons.com" | 35 |
| 29 | 99 | cut | - | ": focus can silently land on the wrong window and capture unrelated private content." | 12 |
| 30 | 101 | condense (todo ids are history) | - | " (`<pid>-<procStart-ticks>`, resolved from `$env:CLAUDE_CODE_SESSION_ID` ... (todo 324)." | 76 |
| 31 | 105 | cut | close/ai-todos-format.md | "Written by `/close`, `/create-todo`, `/code-check`, autopilot; ordered by `/plan-todos`; ... naming an id - " | 38 |
| 32 | 108 | condense | close/ai-todos-format.md | " Write it there and move on; do not queue it locally ... see `close/ai-todos-format.md`." | 48 |
| 33 | 113 | cut (history) | - | " ai_todos moved OUT of here to `.claude/todos/` on 2026-07-15; ... unmigrated legacy." | 32 |
| 34 | 117 | cut (example list) | - | " (Riverpod / context / useState / module-scope)" | 12 |
| 35 | 121 | cut | global-knowledge-vault.md:45-46 holds it | " The vault is shared across 3+ concurrent sessions with no file locking ... never whole-file." | 38 |
| 36 | 129 | move | memory-rubric.md (add paragraph) | "is harness-internal advisory, not a rule to obey - it re-fires ... later run `/cleanup-memory`." | 44 |
| 37 | 133 | cut | - | ", even an ad-hoc one with no skill in the loop" | 12 |
| 38 | 140 | cut | - | " A single-fact lookup (one version check, one typosquat check) stays inline." | 19 |
| 39 | 146 | cut (restates the heading) | - | " A well-written dispatch prompt (precise spec, file paths, constraints, report-back shape) determines subagent quality." | 30 |
| 40 | 156 | condense | delegation-doctrine.md | "The rules above govern ordinary dispatches. A pure ORCHESTRATOR session ... not by default." | 57 |
| 41 | 7 | cut | - | "Replaces the caveman plugin (uninstalled) - " | 11 |
| 42 | 11 | cut (example) | - | " E.g. \"Claude will write them to Clockify\" ... \"you'll write them\"." | 31 |
| 43 | 23 | cut | - | " (a settings.json edit, a newly installed skill or hook)" | 14 |

**Not in the list, for Joe's call.**
- Line 60 (supervisor fallback: "Fall back to a plain shell run only if the supervisor is unreachable") contradicts
  `hooks/dev-server-guard.py` (todo pc-1278). It is a content change, not a size cut, so it stays out of the 43.
- Rules the refuter flagged as partly load-bearing were only condensed, never cut: the shell-write ban (item 12,
  hook fails open) and the MEMORY.md never-delete-an-index-line rule (kept whole, plus the new tier-exception clause).
- Line 32 (client commit window, 190 chars) and the `.for_bepy` section are small and already pointers; left alone.
- Path-scoped `~/.claude/rules/` (done todo pc-0424) is a separate decision and not part of this list.
- Line 152's "Agent has no effort parameter" and the effort-parameter wording were fixed tonight under todo 1270.

Left open and unclaimed for Joe's morning review; apply = run the script's replacements, then re-run
`python ci/check_instruction_budget.py` and lower `CEILING_TOKENS` toward the new size (it is a ratchet).
