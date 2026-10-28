<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=5, reconfirm-count=2, content-hash=9a2649b8 -->
# flutter-web-playwright.md's "release build, not DWDS" guidance is stale/incomplete

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix `~/.claude/refs/flutter-web-playwright.md`'s "Release build, not DWDS" section (and the
`flutter-e2e` skill's Mode A, which cites it) so a future session doesn't waste time building an
unused release bundle when a debug `flutter run -d web-server` session would have worked fine.

## Context

zng-admin session, 2026-08-10 (verifying a biller-group creation fix). The doc flatly states:
"Drive a `flutter build web` release bundle served statically instead; debug/DWDS sessions are
not drivable by raw Playwright" and gives no exception. Following it, I built a release bundle
(`flutter build web -o build/web-e2e`, ~70s) and served it via supervised-run before even trying
the already-running debug session.

It turned out unnecessary: the exact same target app, same route, driven against the **live debug
`flutter run -d web-server` session** (no release build), worked perfectly using
`page.getByRole('textbox')` / `page.getByText(...)` / `page.getByRole('button', {name})` â€” this
matches prior-art scripts already in the zng-admin repo (`.for_bepy/qa54714-common.cjs`,
`.for_bepy/qa-d5-biller-create.cjs`), which clearly also drive the debug session successfully via
the same locator style. My own manual `flt-semantics-placeholder` activation attempts (evaluate
click, synthetic PointerEvent, even a real trusted `page.mouse.click()`) all failed â€” 0 semantics
nodes â€” but simply calling `getByRole`/`getByText` (no manual activation at all) worked
immediately. Likely explanation: Playwright's own accessibility-tree queries (what those locators
use under the hood) themselves trigger Flutter's semantics activation, independent of any click â€”
so the doc's premise ("Playwright's own CDP session conflicts with DWDS and the page hangs
forever") may only hold for the specific case of driving the raw `flt-semantics` DOM by hand /
opening a second cold CDP connection to an already-connected DWDS session, not for role/text
locators against a freshly-loaded page.

Recorded as a project memory too:
`C:\Users\tecno\.claude-personal\projects\C--Users-tecno-Desktop-Projects-zng-admin\memory\feedback_playwright_no_mcp_fallback.md`
(2026-08-10 addendum) â€” that's the zng-admin-specific pointer; this todo is for fixing the
shared/global doc so every project stops re-learning it.

## Approach

- Re-test carefully (don't just take this session's single data point as gospel) whether
  `page.getByRole`/`page.getByText` locators reliably work against a live `flutter run -d
  web-server` debug session with NO manual semantics activation, across a couple of different
  Flutter apps/versions, not just zng-admin.
- If confirmed broadly: rewrite the "Release build, not DWDS" section to say role/text locators
  ARE fine against DWDS; reserve the release-build requirement for whatever narrower case
  actually breaks (manual `flt-semantics` DOM scraping? a second concurrent CDP connection?).
- If it's zng-admin-specific (e.g. because this app already force-enables accessibility another
  way): qualify the doc instead of rewriting it wholesale, and note the exception.
- Either way, add a pointer in `flutter-e2e`'s Mode A: before building a release bundle, check the
  target project for existing `.for_bepy/*.cjs`/`.for_bepy/e2e/*.cjs` driver scripts and reuse
  their pattern (auth seeding, locator style) instead of re-deriving driving mechanics from
  scratch â€” this repo alone had 15+ prior one-off `qa*.cjs` scripts that already solved this.

## Acceptance

- `flutter-web-playwright.md`'s DWDS section reflects the tested truth, with the evidence/date
  that produced the update (not just a flipped claim).
- `flutter-e2e`'s Mode A tells the agent to check for existing project e2e helpers first.

## Notes

Not urgent â€” the workaround (try locators against the debug session first, fall back to release
build only if that fails) is cheap once known. This todo is about updating the doc so the next
session doesn't rediscover it the expensive way.
- completed, commit c2dca59. The 2026-08-10 observation is now recorded as a single untested data point with an explicitly-marked unverified hypothesis, not a new absolute; the release-build fallback stays as the safety net. Re-testing against a live DWDS session is still open.
