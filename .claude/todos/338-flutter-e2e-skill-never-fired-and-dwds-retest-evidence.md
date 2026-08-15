<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=7, reconfirm-count=1, content-hash=0750de4e -->
# flutter-e2e never fired for a whole day of Flutter web e2e, and there's now hard DWDS re-test data

**Type:** skill-improvement
**Origin:** ai

## Goal

Two related gaps from one session: the `flutter-e2e` skill did not fire for an entire day of
Flutter web browser automation, and that session produced exactly the DWDS re-test evidence todo
`74` left open in its Notes.

## Context

zng-admin, 2026-08-14. A session ran **five** separate Playwright e2e dispatches across a full day
(mask toggle, roles popup, navigation fix, duplicate-slug regression, last-active-mask warning).
`flutter-e2e`'s own description covers this exactly: *"run an e2e test", "drive the app through a
flow", "test this flow in the browser", or any Flutter web QA/automation ask.* It was never
invoked once. The orchestrator hand-wrote every dispatch prompt instead, pasting the same
canvas-driving rules block (semantics activation, atomic evaluate-dispatched clicks, per-character
typing, sidebar has no semantics nodes) into each one by hand, and independently rediscovered the
release-build fallback that the skill's Mode A already checks for.

Two plausible causes, both worth checking before touching the skill:
1. The skill is not model-invocable from an orchestrator that is dispatching subagents rather than
   driving the browser itself, so it never surfaced as an option.
2. Subagents cannot invoke skills at all, so an orchestrator delegating e2e has no path to the
   skill's content except copying it into the prompt by hand. If that is the real constraint, the
   fix is not in `flutter-e2e` but in `delegation-doctrine.md`: a dispatch that delegates
   browser work should be told to hand the subagent the skill's file path to read, rather than
   re-typing its rules.

**The DWDS evidence todo `74` asked for.** `74` is in `done/`, and its resolution deliberately
recorded the 2026-08-10 "role/text locators work fine against a live debug session" observation as a
single untested data point, leaving the release-build fallback as the safety net and re-testing
explicitly open. This session is that re-test, and it went the other way:

- Round 1 against `flutter run -d web-server`: some routes rendered, but `/billers/<id>` and
  `/users/<id>` each hung ~4.5 min and never mounted, while a later route in the same session
  mounted instantly.
- Round 2, against a **freshly restarted** process (so, its first-ever browser connection): never
  painted at all in a 180s budget. `curl` confirmed the server itself healthy and `main.dart.js`
  served in single-digit ms as the ~8.7 KB DWDS bootstrap stub.
- Switching to `flutter build web` + a static file server: worked on the first attempt, and every
  subsequent round too. `main.dart.js` ~3.9 MB of real compiled output.

Cost of the detour: roughly two hours across two blocked rounds plus a killed agent.

## Approach

1. Decide which of the two causes above is real. If subagents genuinely cannot invoke skills, add a
   line to `~/.claude/refs/delegation-doctrine.md`'s canonical builder preamble telling delegated
   browser work to READ `~/.claude/skills/flutter-e2e/` and `~/.claude/refs/flutter-web-playwright.md`
   rather than having the orchestrator paste their contents.
2. Update `~/.claude/refs/flutter-web-playwright.md`'s "Release build vs a live debug (DWDS) session"
   section with this session's evidence. Do NOT flip it back to an absolute: keep both data points
   with their dates and conditions, and state the practical rule that actually follows, which is
   roughly "try the debug session if one is already warm, but for a multi-scenario sweep go straight
   to a release bundle, because retries are free there and a stall is unrecoverable."
3. Consider whether `flutter-e2e`'s Mode A should just default to the release bundle for any sweep of
   more than one scenario, instead of checking.

## Acceptance

- A session doing Flutter web e2e either fires `flutter-e2e`, or its dispatch prompts point the
  subagent at the skill's files instead of hand-copying the rules.
- `flutter-web-playwright.md` carries both the 2026-08-10 and 2026-08-14 observations with
  conditions and dates, and a rule a reader can act on without re-deriving it.

## Notes

- Follows up [[74-flutter-web-playwright-dwds-guidance-stale]] (in `done/`), whose own Notes left
  this re-test open. Not a duplicate of it: 74 shipped the softening, this carries the counter-evidence
  and the separate skill-never-fired problem.
- Related: `306` built `restart-and-wait.ps1` for the restart-then-poll half of the dance. That
  helper does not help here, since the failure was the browser attach, not readiness detection.
- The zng-admin-specific version of this lesson is already recorded in that project's
  `reference_zng_admin_dev_login` memory, including the build command and the static-server caveat
  about no SPA fallback. This todo is for the shared tooling.
