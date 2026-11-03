<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped the backlog and done/ for "zng-kickoff" and "kickoff.py", no prior entry -->
# zng-kickoff: harden kickoff.py from the 8347382 code-check

**Type:** task
**Origin:** ai
**Summary:** The kickoff script never silently drops feed events, never lists a non-frontend ticket as pickable, and reports leftovers as its docs say, with tests.

## Why

Found by the 2026-10-26 /close code-check of commit 8347382: the feed cap loses old events for good and the title search has no local filter.

## Goal

`skills/zng-kickoff/scripts/kickoff.py` never silently drops feed events, never lists a non-FE ticket
as pickable, and reports leftovers the way SKILL.md says it does. Its resurfacing rules are covered
by tests.

## Context

From the `/close` code-check of 8347382 on 2026-10-26, done in a fresh subagent. Later commits
53dbefa and dcd977a did not touch any of these. Line numbers are from HEAD on 2026-10-26.

1. **Feed cap drops events for good** (class 3). `cmd_feed` loops `for _ in range(60)` (~156). If it
   ends on that cap before reaching `stop_at`, it still sets `high_water` to the newest cached event
   (~174). The older gap is never fetched on a later run, which breaks SKILL.md's promise that
   activity resurfaces.
2. **`title:` search has no local post-filter** (class 3). `cmd_tickets` queries `title:FE`, `title:"Web App"`
   and `title:Frontend`. `refs/shortcut-api.md` "Searching stories" says `title:` matching is
   fuzzy/substring and needs a local post-filter on `name`. The script only drops BE-prefixed names.
   Decision inside: owner-query hits (the dev's and Peter's) should stay exempt from the name filter.
3. **Leftovers wording vs output** (class 2). When a branch has no `@{u}`, `git()` returns
   `(git error: ...)` and `cmd_leftovers` prints it as `unpushed (git error: ...)`. SKILL.md step 2
   says the script "lists ... dirty files", but it prints only a count. A failed fetch is ignored
   silently.
4. **Test gap** (class 2). The per-ticket aggregation in `cmd_feed` has no test: handled mark vs
   newest non-dev activity, the noise-only filter, and dev-authored events not counting as
   activity. Neither have `cmd_tickets` and `cmd_leftovers`.

## Approach

1. Track whether the feed loop reached `stop_at`. If it didn't, print a warning and keep the old
   `high_water`, so the next run fetches the rest.
2. After merging ticket search results, keep a story only if it came from an owner query, or its
   `name` matches `\bFE\b`, `Web App` or `Frontend`.
3. Print `no upstream` when `@{u}` doesn't resolve, print the dirty paths (or reword SKILL.md step
   2), and print a line when `fetch` fails.
4. Extract the per-ticket aggregation into a pure function. Test it, plus `cmd_tickets` with a
   stubbed `api_get`, in `scripts/test_kickoff.py`.

## Acceptance

- New tests fail without each fix and pass with it: cap-hit keeps `high_water`, a fuzzy non-FE
  title is filtered out, an owner-query ticket is kept, no-upstream prints `no upstream`.
- `python skills/zng-kickoff/scripts/test_kickoff.py` and `python ci/run_all.py` pass.

## Notes

- Fixed in e4d4d4a together with pc-1256, pc-1250 and pc-1262 (same files).
