<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 02/496/965 share only generic words (with, stop, retry); none is about zng-kickoff -->
# zng-kickoff feed: retry a 401 with the full header set, warn on the page cap, and stop printing git errors as commits

**Type:** task
**Origin:** ai
**Summary:** The kickoff feed retries a 401 with the full header set, warns on the page cap, and shows a no-upstream branch as unpushed work.

## Why

Found by the 2026-10-28 per-commit review of 8347382: a valid cookie can be reported dead, old events are silently lost, and a git error prints as a commit line.

## Goal
`skills/zng-kickoff/scripts/kickoff.py` stops reporting a valid Shortcut cookie as dead, stops silently losing old feed events, and shows a no-upstream branch as unpushed work instead of a fake commit line.

## Context
Found by the 2026-10-28 per-commit review of 8347382 (pre-push gate, release session).
- `kickoff.py:122-129` and `:161-162`: `fetch_page` sends only the trimmed header set (accept, content-type, tenant headers, x-requested-with, cookie) and treats the first 401/403 as "SHORTCUT_SID is dead". `skills/shortcut-priorities/SKILL.md` (685bfd2) documents that this exact set returns `401 profile_invalid` for a valid cookie and that the first 401 must be retried with the full browser set (`origin`, `referer`, `user-agent`, `clubhouse-page`, `shortcut-action-context`).
- `kickoff.py:156-174`: pagination stops at 60 pages but `high_water` is set to the newest event anyway, so events past page 60 fall below the mark and are never fetched; nothing is printed.
- `kickoff.py:110-115`: `git()` returns the string `(git error: ...)`; for a branch with no upstream, `@{u}..HEAD` fails and the output shows `unpushed (git error: fatal: no upstream...)`.
- `kickoff.py:60-79`: `env()` strips whitespace and BOM but not surrounding quotes; `skills/ticket/scripts/shortcut_triage.py:45-71` (`read_token`) strips quotes and has a test. A quoted `SHORTCUT_API_TOKEN` would 401. UNVERIFIED whether the live .env value is quoted.
Todo 1249 already covers other kickoff hardening (feed cap wording, title filter); check it first and merge rather than duplicate.

## Approach
Mirror shortcut-priorities' 401 retry with the full header set; on hitting the page cap print a warning and keep `high_water` at the oldest fetched event; make `git()` failures distinguishable and render no-upstream as "no upstream, N local commits"; strip quotes in `env()` or reuse `shortcut_triage.read_token`.

## Acceptance
`skills/zng-kickoff/scripts/test_kickoff.py` gains a case per fix (mocked 401-then-200, page-cap warning, no-upstream branch, quoted token) and passes.
