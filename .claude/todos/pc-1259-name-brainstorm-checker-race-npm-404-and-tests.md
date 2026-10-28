<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 242 and 282 are about the /brainstorm skill, not /name-brainstorm's availability checker -->
# name-brainstorm: checker bootstrap race, npm 404 false FREE, missing tests, view-cache skips .co

**Type:** task
**Origin:** ai
**Summary:** The /name-brainstorm availability checker gives correct results under concurrency, does not call an unpublished npm name free, and its scripts have tests.

## Why

Found by the 2026-10-28 pre-push code-check of 2ae0d60: a bootstrap race, an npm 404 counted as FREE, no tests, and .co results never shown.

## Goal
`/name-brainstorm`'s availability checker reports correct results under concurrency, does not call an unpublished npm name FREE, and its pure scripts are covered by tests.

## Context
Found by the 2026-10-28 pre-push code-check and review of 2ae0d60. (The capital-Đ drop and the dead README-check.md pointer were fixed in 3bcc84d.)
- `skills/name-brainstorm/check-availability.mjs:236-252`: `loadBootstrap` sets `bootstrap = {}` before awaiting the IANA fetch and returns it whenever truthy, so the first ~5 concurrent callers get `{}` and fall back to `FALLBACK_RDAP`. Benign today (fallback covers com/dev/app/io/ai) but wrong once IANA's URL differs.
- `check-availability.mjs:410-421`: npm 404 counts as FREE, but an unpublished package also 404s and usually cannot be republished. UNVERIFIED how often this matters.
- No tests for `view-cache.mjs` (status letters) or `check-availability.mjs`'s offline parts (`parseArgs`, `readNames`, `Gate`, `withRetry`). `ci/run_all.py` picks up `skills/**/test_*.cjs`.
- `view-cache.mjs` `kinds` omits `co`, so `--extra co` results never show.

## Approach
Memoise the bootstrap promise; mark an npm 404 as UNKNOWN or check the registry's unpublished marker; add `test_view_cache.cjs` and an offline `test_check_availability.cjs`; add `co` to `kinds`.

## Acceptance
New tests pass in `python ci/run_all.py`; a concurrent run's first lookups use IANA data (assert via a stubbed fetch).
