<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1186 is about feed lag and scope (workable-now tier), not this request itself failing. 234 (done) added pagination + liveness probe but used the same incomplete header set this todo is about. -->
# 1201 - shortcut-priorities activity probe misdiagnoses a cookie as dead when headers are the real gap

**Type:** skill-bug
**Origin:** ai
**Created:** 2026-10-19

## Goal

The private activity endpoint's liveness probe (SKILL.md Step 0/2) should not tell Joe his session
cookie is dead when the real cause is a missing header in the Python request.

## Context

zng-app session, 2026-10-19, `/shortcut-priorities` (past day). The cached `SHORTCUT_SID` /
`SHORTCUT_TENANT_ORG` / `SHORTCUT_TENANT_WS` in `~/.claude/.env` were valid the entire time. Step 0's
probe (urllib, headers: `accept`, `content-type`, `tenant-organization2`, `tenant-workspace2`,
`x-requested-with`, `cookie`) returned `401 {"tag":"profile_invalid"}`. Per the skill's own Step 0
text, a 401 means "ask Joe for a fresh cookie" - so three rounds of "Copy as cURL" were requested
from Joe, burning his time, before testing with `curl` directly using the *same unchanged* cached
credentials.

`curl` with the exact same `sid`/org/ws succeeded (`201`, real data back to 2026-10-16). The only
difference: `curl` carried extra headers the browser's real request has that Step 0/2's snippet
never lists - `origin: https://app.shortcut.com`, `referer: https://app.shortcut.com/zirtue/...`,
`user-agent`, `clubhouse-page: stories`, `shortcut-action-context: stories`. Adding just `origin` +
`referer` + `user-agent` to the Python request was not tested in isolation; all five were added
together and confirmed working. The server returns the same generic `401 profile_invalid` body for
"bad/expired cookie" and "well-formed cookie but the request looks non-browser-like", so the probe
cannot currently tell these apart.

## Approach

In `C:\Users\tecno\.claude\skills\shortcut-priorities\SKILL.md`:

- Add the five headers above (or at least `origin`, `referer`, `user-agent` - narrow down which are
  actually load-bearing vs cargo-culted from the cURL paste) to both the Step 0 probe snippet and
  the Step 2 pagination snippet.
- Note in Step 0 that a `401`/`403` with `tag: profile_invalid` (or any tag) is NOT reliable proof
  the cookie is dead - the same error covers a malformed/incomplete request. Before asking Joe for a
  fresh cookie, retry once with the full browser-shaped header set; only ask if that retry also 401s.

## Acceptance

- A probe run with a genuinely valid cached cookie succeeds without a header-shape regression.
- Re-reading Step 0 after the fix, a model following it literally would not ask Joe for a new cookie
  on the first 401 - it would retry with full headers first.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): shortcut-priorities sends a shared full browser HEADERS set and retries once on 401/403 before calling the cookie dead. Not run live.
