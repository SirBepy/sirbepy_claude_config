---
name: flutter-e2e
description: Triggers on /flutter-e2e only. Drives a Flutter web app through a flow with raw Playwright against Firebase emulators - release build, static serve, atomic semantics clicks, REST seed/assert.
argument-hint: "<flow-description-or-existing-script>"
---

# /flutter-e2e

> Drive a Flutter web RELEASE build through a scripted flow with raw Playwright against local Firebase emulators, seeding and asserting Firestore/Auth state, without rediscovering the DWDS/stale-node/headless landmines.

This is the gate-free, reusable version of what was first built by hand for `pomalo` (overnight run, 2026-07-17). Use it whenever a flow needs to run **unattended, from cold, against Firebase emulators** (auth + data round trips, overnight verification, CI-style smoke tests).

## Not the same job as /test-flow

`/test-flow` drives a **debug** build already running via the dev's own `flutter run` (F5), through Playwright MCP, with the dev present to log in. It explicitly never starts/stops the dev server and never touches credentials.

`/flutter-e2e` is the opposite shape: it builds and serves a **release** bundle itself, starts the emulators itself, signs in through the **auth emulator** (no real credentials), and drives raw Playwright (not MCP) because MCP's locate-then-click round trip is exactly what breaks on Flutter's semantics tree (see Step 4). Use `/flutter-e2e` when you need Firebase-emulator-backed automation; use `/test-flow` for human-supervised manual QA against a running debug session.

## Preconditions (check first, don't assume)

- `firebase.json` has an `emulators` block with `auth` and `firestore` ports (defaults 9099 / 8080). If missing, add it - do not invent a project without checking `firebase_options.dart` / `firebaseConfig` for the real project id first.
- The app has an emulator-mode switch gated on a compile-time define, e.g. checks for `--dart-define=USE_EMULATORS=true` and calls `useAuthEmulator` / `useFirestoreEmulator` when set. If the app has no such switch, stop and ask how emulator mode is toggled instead of guessing.
- Node + a Playwright install reachable (`npx playwright` or a local `node_modules/playwright`). Note the resolved path; you'll need it as a literal `require()` path in the driver script if it's not in the project's own `node_modules`.
- `fvm` (or plain `flutter`) on PATH, matching the project's usual invocation.

## Step 1 - Start the Firebase emulators

Via `/supervised-run` (never bare in your own shell - it must survive the driver script's lifetime):

```
firebase emulators:start --only auth,firestore
```

Reuse an existing supervised entry if one's already running (see supervised-run's list-before-create rule). Ports come from `firebase.json`, not dynamic - use `"use_dynamic_port": false`.

## Step 2 - Build the RELEASE web bundle

**This is not optional and not a style choice.** `flutter run` web (debug) uses DWDS, which needs its own CDP debugger attachment - Playwright's CDP session conflicts with it and the page hangs forever at "DDC is about to load ... scripts", no error, no timeout. A release build has no DWDS in the loop:

```
fvm flutter build web --dart-define=USE_EMULATORS=true -o build/web-e2e
```

Rebuild whenever app code changes; the static bundle does not hot-reload.

## Step 3 - Serve the release bundle statically

Via `/supervised-run` (kind `generic`, dynamic port), e.g.:

```
python -m http.server {PORT} --directory build/web-e2e
```

(or `npx serve build/web-e2e -l {PORT}` if Python isn't available). Note the resulting URL - this is your `APP_URL` for the driver script.

## Step 4 - Write the Playwright driver script

Copy `references/e2e-helpers.js` (next to this file) into the project, e.g. `.for_bepy/e2e/helpers.js`, and fill in its `CONFIG` block (`APP_URL` from Step 3, `FIREBASE_PROJECT_ID` from `firebase.json`, `SHOT_DIR`/`E2E_DIR` paths). Then write a driver script (`.for_bepy/e2e/run.js` or similar) that `require()`s it. Non-negotiable rules baked into the helpers, restated here so you don't undo them by hand-rolling around them:

- **Launch `headless: false`.** The auth-emulator Google sign-in popup relay hangs forever under headless chromium - this is the single most common silent hang in this technique.
- **Enable semantics once per page load** via `enableSemantics(page)` (clicks `flt-semantics-placeholder`) before querying anything - Flutter web renders to canvas and has no DOM until this fires.
- **Snapshot with `refreshSemantics(page, tag)` between steps**, not once at the top. It dumps every `flt-semantics` node (aria label, role, x/y center) to `<E2E_DIR>/semantics-<tag>.json` - inspect these when a step can't find its target.
- **Use `clickNodeAtomic(page, /pattern/i)` for anything just created or changed by the previous action** (confirm bars, toasts, a button whose label/count depends on prior state). It does the find-and-click inside one synchronous `page.evaluate()`. A two-step "get coordinates, then click" - even via MCP `browser_click` - has a round-trip gap where Flutter has already recreated the node; the click lands on a dead reference and silently no-ops. This one cost hours to first diagnose - don't skip it because a step "looks simple."
- **Use `clickNode(page, node)` (two-step, from a `dumpSemantics` snapshot) only for stable widgets** you have not just interacted with.
- **Sign in with `signIn(page, context, email, displayName, postSignInBodyPattern)`.** Drives the "Continue with Google" button, then the auth-emulator relay tab (`#add-account-button` -> `#email-input` -> `#sign-in`). Retries up to 3 times; emulator relay popups occasionally fail to load on the first try.
- **Never rely on a full page reload mid-flow.** Emulator mode has an upstream quirk (flutterfire#5372, wontfix): reload drops the emulator auth session because the JS SDK races restore vs `useAuthEmulator`, hits production `identitytoolkit`, 400s, and wipes IndexedDB. Drive everything through in-app navigation instead (Flutter streams update live without a reload). Production is unaffected - this is emulator-only.
- Screenshots go to `.for_bepy/screenshots/` via `shot(page, name)` (gitignored, disposable).

## Step 5 - Seed and assert via emulator REST

No app code changes needed to set up or verify state:

- Firestore: `http://127.0.0.1:<firestore-port>/v1/projects/<project-id>/databases/(default)/documents/<collection-path>`, header `Authorization: Bearer owner` for both reads and writes (any bearer token is accepted by the emulator; `owner` is a convention, not a real credential). `fetchJson(url, opts)` in the helpers wraps this.
- Auth: `http://127.0.0.1:<auth-port>/emulator/v1/projects/<project-id>/accounts` lists/deletes emulator user accounts.
- Pull the signed-in uid out of IndexedDB with `getUidFromIndexedDb(page)` (reads `firebaseLocalStorageDb`) rather than scraping it from the UI or network log - works against any `firebase_auth` app unmodified.

## Step 6 - Report

Summarize pass/fail per driven step, list any new console errors (`page.on('console')` / `page.on('pageerror')`), and point to the screenshots and `semantics-*.json` snapshots saved for this run. Do not commit anything from `.for_bepy/` (it's gitignored scratch) unless the dev explicitly asks to keep a script.

## Acceptance checklist (self-verify before calling a run done)

- [ ] Built with `flutter build web` (release), never driven against a `flutter run` debug session
- [ ] Emulators running with `--dart-define=USE_EMULATORS=true` baked into the build
- [ ] Browser launched `headless: false`
- [ ] `flt-semantics-placeholder` clicked before the first query on every fresh page load
- [ ] Every click on a just-changed/just-created node used `clickNodeAtomic` (single `page.evaluate`), not a cached locator or two-step query-then-click
- [ ] No flow step depends on a full page reload while signed in via the emulator
- [ ] Firestore/Auth state seeded and/or asserted via the emulator REST endpoints, not just eyeballed from screenshots
- [ ] Screenshots saved under `.for_bepy/screenshots/`
- [ ] Final report lists pass/fail per step plus any new console errors

## Reference

`references/e2e-helpers.js` (next to this file): the full helper module - `shot`, `dumpSemantics`, `enableSemantics`, `waitForSemanticsNodes`, `refreshSemantics`, `findNode`, `clickNode`, `clickNodeAtomic`, `fetchJson`, `waitForBodyText`, `signIn`, `getUidFromIndexedDb`. Copy it in and fill the `CONFIG` block at the top; don't rewrite it from scratch per project.
