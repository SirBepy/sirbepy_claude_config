---
name: flutter-e2e
description: Drives a Flutter web app through a flow with Playwright - scripted mode (raw Playwright, release build, optional Firebase-emulator layer) or plan-file mode (steps through a markdown test plan, marking pass/fail/skip inline). Use for "run an e2e test", "drive the app through a flow", "test this flow in the browser", or any Flutter web QA/automation ask - also /flutter-e2e and /test-flow's plan-file alias.
argument-hint: "<flow-description-or-script> | <path-to-test-plan.md> [free-form args]"
---

# /flutter-e2e

> Drive a Flutter web app through a flow with Playwright, without rediscovering the semantics/staleness/DWDS/headless landmines.

Native Android app via adb (not Flutter web)? Use `android-drive` instead - a different surface.

## Two modes - pick one

- **Scripted mode**: no test-plan file given. Ad hoc or unattended runs from cold - overnight verification, CI-style smoke tests, "drive the app through X and tell me what happens." Builds and serves its own release bundle, writes a raw-Playwright driver script.
- **Plan-file mode**: a markdown test-plan path is given. Supervised manual QA against the dev's own already-running debug session - steps through the plan, marks each line pass/fail/skip inline, never starts/stops the dev server.

## Read first, every run

`~/.claude/refs/flutter-web-playwright.md` - the canonical rules for semantics activation, atomic clicks, per-character typing, snapshot staleness, no-reload-mid-flow, release-vs-DWDS, and headless guidance. This file only states mode-specific flow; it does not restate driving mechanics.

## Login preamble (dev-backed apps)

For any app whose flow starts behind an email-OTP or similar login (e.g. zng-biller, zng-admin), pick one of two paths, don't default to driving the UI:

- **Fast path (default for "just get me authenticated"):** call the dev API directly instead of the browser. `POST <API_URL>auth/login {"email"}` then `POST <API_URL>auth/verify {"userId","code":"000000"}` (both with the project's API-key header) returns the token set. Seed it with `page.addInitScript((tokens) => { localStorage.setItem(...) }, tokens)` **before** the single `page.goto()` call, so session-init code finds a valid session on boot and skips the login screen entirely. No coordinate clicks, no focus/Tab timing, no OTP UI at all. zng-biller's committed reference implementation: `scripts/screenshot-dev.js` (also seeds a portal-switcher/mock-mode localStorage key if asked).
- **Slow path (only when the login flow itself is what's under test):** drive the real UI. Expect an empty or unreliable `flt-semantics` tree in a release/CanvasKit build, coordinate clicks off a screenshot are the reliable DEFAULT here, not the fallback the canonical ref above implies for apps where semantics does populate. Read the real DOM proxy box (`document.querySelectorAll('input, textarea').map(el => el.getBoundingClientRect())`) rather than guessing from a screenshot when a stable target exists. The email field's `Enter`-to-submit (`onSubmitted`) usually works; the OTP screen usually does NOT submit on `Enter` or after typing all digits, it needs an explicit click on the actual "Next step"/submit control. A dev-only shortcut that pre-fills/auto-submits `000000` may exist on dev builds; prefer tapping it over typing digit-by-digit when present.
- **Release build is mandatory either way.** `flutter run -d web-server` (debug/DWDS) never bootstraps under Playwright, `document.body` stays script-only, no `flutter-view`, blank forever, no error. Build `flutter build web --release --dart-define-from-file=<env file>` and serve the static `build/web` output (SPA fallback to `index.html`) instead.

## Shared

Node + Playwright reachable (`npx playwright` or the project's own `node_modules`) - note the resolved path, you'll need it as a literal `require()` path. Screenshots go to `.for_bepy/screenshots/<session-id>/`, the id `rename-session.ps1 -GetId` returns (gitignored, per-session, matching `/close`'s purge scheme), resolved automatically by `e2e-helpers.js`'s `SHOT_DIR` via the shared `session-shot-dir.cjs` helper - never hand-fill the id.

## Capture gotchas (Flutter web)

Read this before any screenshot that will feed `/e2e`'s diff mode or a manual fidelity review - a
bad capture makes every downstream measurement wrong regardless of tool. General to Flutter web,
not one app's quirk (generalized from a zng-app session, todo 362):

- **`enableSemantics` resets the scroll offset.** Capture screenshots BEFORE activating the
  semantics tree (the `flt-semantics-placeholder` click above), or the shot lands scrolled back to
  the top of whatever you'd scrolled to.
- **A full-page pixel diff false-passes past a loading spinner.** A CTA that flashes a spinner
  mid-transition can make an otherwise-broken button "match" the design by accident. Clip the CTA
  bar out of the diffed region (`/e2e diff`'s `--exclude-built`) rather than trusting a whole-frame
  compare.
- **Mouse drag never scrolls Flutter web; wheel does.** And the semantics overlay swallows wheel
  events until `flt-semantics-host` is removed from the DOM - if a scroll step silently does
  nothing, check for that element before assuming the scroll target is wrong.

## Mode A - Scripted

1. Check whether the app uses Firebase (`firebase.json` has an `emulators` block). If yes, read `references/firebase-emulators.md` first and layer its boot/build/sign-in/seed steps in. If no - which is every current zng repo (zng-app/admin/biller run a local zng-api + Postgres instead) - skip that file entirely.
2. Check the project for existing `.for_bepy/*.cjs` or `.for_bepy/e2e/*.cjs` driver scripts before
   writing a new one - reuse their locator style and auth-seeding pattern instead of re-deriving
   driving mechanics from scratch.
3. Build the RELEASE web bundle: `fvm flutter build web -o build/web-e2e` (add `--dart-define=USE_EMULATORS=true` only under the Firebase layer). Rebuild whenever app code changes; the static bundle does not hot-reload.
4. Serve it statically via `/supervised-run` (kind `generic`, dynamic port): `python -m http.server {PORT} --directory build/web-e2e` (or `npx serve build/web-e2e -l {PORT}`). Note the URL as `APP_URL`.
5. Copy `references/e2e-helpers.js` into the project (e.g. `.for_bepy/e2e/helpers.js`), fill in its `CONFIG` block (`SHOT_DIR` is resolved automatically, no need to fill it in), and write a driver script that `require()`s it. The helpers already implement every rule from refs/flutter-web-playwright.md (`enableSemantics`, `clickNodeAtomic`, `refreshSemantics`, `shot`) plus the Firebase-only ones (`signIn`, `fetchJson`, `getUidFromIndexedDb`) - only call the latter if Step 1 loaded that layer.
6. Run the script, capture `page.on('console')`/`page.on('pageerror')`, and report per the checklist below.

## Mode B - Plan-file

Invocation is free-form: `/flutter-e2e <path-to-plan.md> [anything else in plain language]` - no rigid `--url`/`--only-failed`/`--close` flags.

Preconditions, once at start: plan file resolves (else stop and ask); the app is already running (ask the dev for the URL if not stated - this mode never starts or stops his `flutter run`/F5 session); a semantics snapshot returns a non-trivial tree (if empty, tell the dev to confirm a debug build with `ensureSemantics()`, not `--release`).

**Before driving any login/auth step: ask the dev whether the flow may log in with dev credentials.** Don't assume either way.

Plan file format - one markdown checklist item per step: `- [ ]` pending, `- [x]` passed, `- [!]` failed, `- [~]` skipped (this skill sets the last three). Optional indented sub-bullets `- expect: ...` / `- console: ...`. Plain-text notes above a step are context only, never executed.

Execution loop per pending step: read + parse intent -> drive per refs/flutter-web-playwright.md, locating by semantic label/role only, never by coordinate -> wait for settle -> verify (screenshot + diff new console errors/warnings against the last-seen count) -> mark the step, appending a reason/screenshot-path sub-bullet on `[!]`/`[~]` -> write the file immediately (Edit), don't batch updates. Stop hard on a dead browser/connection or a non-200 nav; stop soft (ask the dev) after 3 consecutive `[!]` on dependent steps.

Never edit application code, never add/remove/reorder plan steps, never commit, never close the browser unless asked.

Final report: append a `## Run summary` to the plan file - totals (passed/failed/skipped), new console errors, screenshot dir.

## Acceptance checklist

- [ ] Read refs/flutter-web-playwright.md's driving rules before writing or running any step
- [ ] Mode picked matches the ask (scripted = unattended/cold; plan-file = supervised QA against a plan)
- [ ] Scripted: built RELEASE web, never driven against a `flutter run` debug session; Firebase layer loaded only if the app actually uses Firebase
- [ ] Plan-file: login/auth handling was asked about, never assumed
- [ ] Screenshots under `.for_bepy/screenshots/<session-id>/` (the `rename-session.ps1 -GetId` id)
- [ ] Report lists pass/fail per step (or per driven action) plus any new console errors

## References

- `~/.claude/refs/flutter-web-playwright.md` - driving mechanics, read first, both modes.
- `references/e2e-helpers.js` - Playwright helper module: semantics/click/type helpers for both modes, plus Firebase-only `signIn`/`fetchJson`/`getUidFromIndexedDb`.
- `references/firebase-emulators.md` - optional Firebase layer (boot, build flag, sign-in, seed/assert REST); read only when the target app uses Firebase.
- `~/.claude/skills/e2e/SKILL.md` - the router that delegates here for run mode, and owns the
  design-fidelity diff mode that consumes a screenshot captured per this file's gotchas above.
