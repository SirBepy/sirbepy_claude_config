<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no open todo covers hs_addtime.cjs or hs_preflight.cjs timeouts; done/pc-0390 covered wiring, not retries -->
# HubStaff scripts fail on slow page loads with no retry

**Type:** skill-improvement
**Origin:** ai
**Summary:** `hs_addtime.cjs` failed 8 of 21 entries and `hs_preflight.cjs` failed once, all on HubStaff page-load or dialog-open timeouts, and neither script retries.

## Context
2026-11-06, zng-app `/clockify-reconciliator` run for the week of 2026-11-02. Network was fine (a HEAD to app.hubstaff.com returned 200 right after).
- `hs_preflight.cjs` exited 1 with `page.goto: Timeout 30000ms exceeded` on the weekly URL. The same command passed on a manual rerun.
- `hs_addtime.cjs` with 21 entries returned `ok:false` for 8. One was `page.goto: Timeout 30000ms exceeded` on the daily URL. Seven were `locator('.app-dialog.opened')` not visible within 10s after clicking "Add time". A rerun with only those 8 returned 8/8 ok. The activities API then matched Clockify exactly (1200m), with no duplicates.
Every failure happened before Save was clicked, so a retry at that point cannot create a duplicate entry.

## Approach
In `skills/clockify-reconciliator/scripts/hs_addtime.cjs`, retry an entry up to 2 more times when the failure comes before the Save click (goto timeout, dialog never opened, select or input step). Never retry after Save was clicked: in that case report `ok:false` with a `maybeSaved` flag so the caller verifies through the API. Give `page.goto` in `hs_common.cjs` or the scripts a longer timeout or one retry, and make `hs_preflight.cjs` retry its navigation once before it reports a failure.

## Acceptance
A transient goto or dialog-open timeout no longer leaves an entry `ok:false` when a retry succeeds. A failure after Save is never retried automatically. `hs_preflight.cjs` survives one slow navigation.
