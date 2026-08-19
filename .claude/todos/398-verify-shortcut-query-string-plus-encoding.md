<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Settle whether Shortcut's search API decodes a literal plus as a space

**Type:** task
**Origin:** ai

## Goal

Establish, against the live Shortcut API, whether `search/stories` treats a literal `+` in the query
string as a space or as a literal plus, then make every recipe in this repo use one encoding form
and say why.

## Context

Todo 353 (archived 2026-08-19, commit `9aa16ff`) pointed the two remaining inline `search/stories`
recipes at the canonical one in `refs/shortcut-api.md`. It deliberately did NOT reconcile their
encoding, because the two call sites disagree and nobody has evidence for which is correct:

- `skills/zirtue-release-backfill/reference.md` uses a raw `?query=<urlencoded>&...` URL form.
- `skills/work-recap/zirtue/weekly.md` uses `+` for spaces (already the shape todo 343 left).

353's builder left both untouched with a note that the equivalence is unverified, rather than
folding them onto one form and hoping. That was the right call and it is why this todo exists.

If the two forms are NOT equivalent, one of these recipes silently returns the wrong stories, and a
wrong story list feeds outbound work the dev sends as his own words.

## Approach

1. Check for prior evidence first: `refs/shortcut-api.md`, the Shortcut API docs, and any archived
   todo touching query encoding. A documented answer beats a live call.
2. If none exists, make ONE read-only `search/stories` call each way with a query containing a
   space, using the token the other recipes already read from the environment, and compare result
   counts. Read-only, no mutation, so this needs no outbound ground check.
3. Then either fold both call sites onto the winning form, or document in `refs/shortcut-api.md`
   that both work and why, so the next reader does not re-open this.

## Acceptance

- The question is answered with a receipt: a doc URL fetched, or a real API response.
- Both call sites use the settled form, or the canonical ref explicitly blesses both.
- `refs/shortcut-api.md` records the answer so it is not re-derived.

## Notes

- Do not hardcode a token anywhere. Read it from the environment as the existing recipes do.
