<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-06; grepped backlog + done/ + dropped-findings.log for "findingCacheKey" and "1063", only done/1063 (the change itself) hits. -->
# Confirm impeccable's value-keyed finding cache cannot hide a second occurrence

**Type:** task
**Origin:** ai

## Goal
A recorded answer to whether `findingCacheKey`'s line-free, value-only key can make the stop hook
silently skip a genuinely separate occurrence, plus a comment or a fix to match.

## Context
Found by the 2026-10-06 pre-push /code-check and by a commit reviewer (class 3, judgment).
1f9eb1d (todo 1063) made `findingCacheKey` (`skills/impeccable/scripts/hook-lib.mjs:966-972`) return
`${antipattern}:${value}` whenever `extractFindingIgnoreValue` yields a value, dropping the line on
purpose so a line shift no longer re-flags a known finding. A reviewer reproduced that two findings
with the same antipattern and value at different lines (`overused-font`, line 5 and line 80,
"Primary font: Comic Sans") collapse to one key, so `dedupeAgainstCache` returns one of the two.
UNVERIFIED: whether any `directValueRules` detector (`hook-lib.mjs:853-861`) actually emits one
finding per occurrence rather than one per file and value; would check each detector's emit site.
`hook-lib.test.mjs`'s new cases only cover the snippet branch (`tiny-text`, `dark-glow`).

## Approach
1. Read each `directValueRules` detector's emit site and record whether it can emit two same-value
   findings for one file.
2. If it cannot: say so in the `findingCacheKey` comment. If it can: keep the value for stability
   but disambiguate same-value occurrences (for example by order within one scan), and add a
   value-branch case to `hook-lib.test.mjs`.

## Acceptance
- The comment or the fix lands, and the impeccable test file passes.
- `skills/impeccable` stays a near-verbatim vendor copy apart from this one function.
