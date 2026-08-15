<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=8, reconfirm-count=1, content-hash=84eb3fda -->
# Add a "Login preamble (dev-backed apps)" section to flutter-e2e's SKILL.md

**Type:** skill-improvement
**Origin:** ai

## Goal

Fold the empirically-validated login-preamble recipe (7+ documented occurrences in zng-biller alone) into `~/.claude/skills/flutter-e2e/SKILL.md`, so a cold session driving any dev-backed Flutter web app (email-OTP or similar login) doesn't re-derive the same CanvasKit/coordinate-click/release-build gotchas from scratch.

## Context

Surfaced 2026-08-13 while running `/auto-do-todos` on zng-biller's todos 33/72 (reusable portal-login Playwright helper + reusable screenshot script). The builder subagent drafted this exact section and started to write it directly into the global skill file - caught and reverted before commit, because editing a global `~/.claude` skill from a project-repo session without the dev's explicit say-so in that session is against CLAUDE.md's Subagent-Driven / global-tooling rule. Filing here instead so a session actually working in `~/.claude` can land it deliberately.

zng-biller's own reference implementation now exists and is committed: `scripts/screenshot-dev.js` (+ `.ps1` wrapper) in that repo. It logs in via a fast localStorage-token-injection path (POST the dev API's `auth/login` then `auth/verify` with code `000000`, then `page.addInitScript` to seed the token set before the single `page.goto()`), avoiding the browser-driven OTP dance entirely for the common "just get me authenticated" case.

## Approach

Add this section to `~/.claude/skills/flutter-e2e/SKILL.md`, right after its existing pointer to `~/.claude/refs/flutter-web-playwright.md` (that file covers general driving mechanics and stays app-agnostic; this is dev-backend-login-specific, so it belongs in the mode-specific SKILL.md, not the shared ref):

```md
## Login preamble (dev-backed apps)

For any app whose flow starts behind an email-OTP or similar login (e.g. zng-biller, zng-admin), pick one of two paths - don't default to driving the UI:

- **Fast path (default for "just get me authenticated"):** call the dev API directly instead of the browser. `POST <API_URL>auth/login {"email"}` then `POST <API_URL>auth/verify {"userId","code":"000000"}` (both with the project's API-key header) returns the token set. Seed it with `page.addInitScript((tokens) => { localStorage.setItem(...) }, tokens)` **before** the single `page.goto()` call, so `Session.init()`-equivalent code finds a valid session on boot and skips the login screen entirely. No coordinate clicks, no focus/Tab timing, no OTP UI at all. zng-biller's committed reference implementation: `scripts/screenshot-dev.js` (also seeds a portal-switcher/mock-mode localStorage key if asked).
- **Slow path (only when the login flow itself is what's under test):** drive the real UI. Expect an empty or unreliable `flt-semantics` tree in a release/CanvasKit build - coordinate clicks off a screenshot are the reliable DEFAULT here, not the fallback the canonical ref above implies for apps where semantics does populate. Read the real DOM proxy box (`document.querySelectorAll('input, textarea').map(el => el.getBoundingClientRect())`) rather than guessing from a screenshot when a stable target exists. The email field's `Enter`-to-submit (`onSubmitted`) usually works; the OTP screen usually does NOT submit on `Enter` or after typing all digits - it needs an explicit click on the actual "Next step"/submit control. A `DevComponent` shortcut that pre-fills/auto-submits `000000` may exist on dev builds - prefer tapping it over typing digit-by-digit when present.
- **Release build is mandatory either way.** `flutter run -d web-server` (debug/DWDS) never bootstraps under Playwright - `document.body` stays script-only, no `flutter-view`, blank forever, no error. Build `flutter build web --release --dart-define-from-file=<env file>` and serve the static `build/web` output (SPA fallback to `index.html`) instead.
```

## Acceptance

- The section lands in `~/.claude/skills/flutter-e2e/SKILL.md` verbatim or close to it.
- A future cold session driving a dev-backed login picks the fast path by default without rediscovering the localStorage-injection trick.

## Notes

Before landing this: run the content-duplicate guard (grep this backlog and `done/` for "login preamble" / "flutter-e2e" / prior OTP-driving todos) - none found as of 2026-08-13, but re-check at execution time in case another session filed something adjacent since.
