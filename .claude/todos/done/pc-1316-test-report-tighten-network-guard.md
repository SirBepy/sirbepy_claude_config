<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new skill from pc-1315, whose scope did not cover this. -->
# /test-report: make the recording's network guard actually block and fail the take

**Type:** task
**Origin:** ai
**Summary:** A recorded test should fail loudly if it tries a deployed backend, and the allowed hosts should be exact.

## Goal

A take that tries to reach a deployed backend fails visibly, and only the named CDN hosts get past the block.

## Context

Found by /code-check on commits f75775f, 70de46f and 90d24d1.

- `skills/test-report/scripts/recorder.cjs:75`: `page.on('request', ...)` throws when a URL matches `refuseUrls`. The event fires after the request starts, and the throw is not inside the script's try/catch, so it does not reliably fail the take. UNVERIFIED what Playwright does with that throw: check by running a take against a matching URL.
- `recorder.cjs:15`: the default `allowHosts` is an unanchored regex (`/gstatic\.com|googleapis\.com|jsdelivr|fonts\./`), so `firestore.googleapis.com` and any host merely containing those strings pass. The comment at `recorder.cjs:62` says "Nothing may leave this machine", which that regex contradicts.
- The route in `recorder.open` already stubs every other non-local host, so a deployed backend outside `allowHosts` gets a fake 200 rather than a real request. That limits the risk, and it also hides the mistake.
- Node `fetch` in a project's `lib.cjs` (sign-in) is outside all of this.

Why it matters: past runs against the dev backend paged the team (zng-app memory `feedback_never_test_against_dev_backend`).

## Approach

1. In the `context.route` handler, check `refuseUrls` first: abort, and record the URL on the session state.
2. `finish` throws, or marks the take failed, when any refused URL was recorded.
3. Anchor `allowHosts` to the exact hosts a Flutter web build needs, confirmed from a take's `outside` list, and make the comment say what it allows.

## Acceptance

- A take that requests a URL matching `refuseUrls` ends with a visible failure, and nothing reaches that host.
- A Biller Groups take still renders, with its fonts.

## Notes

- fixed: recorder routes every request, aborts and records refuseUrls matches (even on allowed hosts), finish throws; allowHosts anchored to www.gstatic.com, fonts.gstatic.com, fonts.googleapis.com, cdn.jsdelivr.net. Test skills/test-report/scripts/recorder.test.cjs (fake Playwright, red on the old recorder). The host list is Flutter web's known CDN set, not read from a live take's outside list: a Biller Groups take is verify only.
