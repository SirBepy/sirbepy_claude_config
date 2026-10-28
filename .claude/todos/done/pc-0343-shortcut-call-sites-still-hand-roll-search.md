<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Three Shortcut skills still hand-roll search/stories instead of using the new shared recipe

**Type:** skill-improvement
**Origin:** ai

## Goal

Point the existing Shortcut search call sites at the shared recipe that now exists, so the query
shape lives in one place instead of three, matching how `shortcut-update-ticket` already defers to
the ref for its mutation recipe.

## Context

Todo 327 landed 2026-08-15: `refs/shortcut-api.md` gained `Fetching a story with comments` and
`Searching stories` sections, covering the GET recipes, the query operators, `.next` pagination and
the `title:` colon-substring gotcha. That todo's Approach did not ask for a refactor of existing
call sites, so its builder correctly left them alone and reported them.

The three that still hand-roll their own `search/stories` curl call:

- `skills/shortcut-pickup-ticket/SKILL.md:26-30` - `query=owner:josipmui !is:archived`,
  `page_size=10`, no pagination.
- `skills/shortcut-done-audit/SKILL.md:58-63` - `page_size=25` plus `.next`-cursor pagination until
  exhausted, then a client-side filter on `workflow_state_id` because the search API rejects
  `workflow_state_ids` as a POST body key.
- `skills/work-recap/zirtue/weekly.md:87-105` - two separate calls, `completed:<buffer_start>..*`
  and `!is:done`, both `page_size=25`, paginated with a stop at roughly 50 results.

Also spotted while filing this: `refs/shortcut-api.md`'s own header lists the skill family as
`shortcut-create-ticket, shortcut-pickup-ticket, shortcut-done-audit, shortcut-priorities` and omits
`shortcut-update-ticket` and `work-recap`, both of which already reference the file. Pre-existing
drift, worth fixing in the same pass since it is one line.

## Approach

Per call site, replace the inline curl recipe with a pointer to `refs/shortcut-api.md`'s
`Searching stories` section plus only the parts that are genuinely site-specific: the query string
itself, the page size, and any client-side filter the API cannot express.

Do not flatten away the differences that are real. `shortcut-done-audit`'s client-side
`workflow_state_id` filter exists because the API rejects that key, and `work-recap`'s stop-at-50
is a deliberate bound. Those stay at the call site; only the mechanics move.

Check whether the ref's recipe actually covers all three query shapes before rewriting any of them.
If it does not, extend the ref first, in the same pass.

Fix the header line while there.

## Acceptance

- No skill file contains a hand-written `search/stories` curl invocation that the ref already
  documents.
- Each call site still states its own query, page size and any client-side filter.
- The ref's header names every skill that references it.

## Notes

- Done 2026-08-16, commits 8abd412 and 330a59e. shortcut-pickup-ticket, shortcut-done-audit and work-recap/zirtue/weekly.md now point at refs/shortcut-api.md's Searching stories recipe, keeping only their own query, page size and client-side filters. The ref's header lists every referencing skill again. Three more inline recipes exist outside this todo's named scope (ground-check.md, shortcut-create-ticket SKILL.md:81, zirtue-release-backfill/reference.md:16) and were deliberately left alone. The follow-up FIX commit removed two em dashes the refactor introduced, caught by /commit's em-dash prefilter.
