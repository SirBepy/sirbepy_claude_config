# Firebase emulator layer (optional)

Only read this when the target app actually uses Firebase (`firebase.json`
has an `emulators` block, `firebase_options.dart`/`firebaseConfig` exist).
Joe's zng repos (zng-app, zng-admin, zng-biller) run a local zng-api +
Postgres instead - skip this file entirely for those; there is no emulator
layer, no seed/assert REST, no `signIn`/`getUidFromIndexedDb`. Drive their
state through the app's own local API or a direct DB query instead.

## Preconditions

- `firebase.json` has an `emulators` block with `auth` and `firestore` ports
  (defaults 9099 / 8080). If missing, add it - confirm the real project id
  from `firebase_options.dart`/`firebaseConfig` first, don't invent one.
- The app has an emulator-mode switch gated on a compile-time define (e.g.
  `--dart-define=USE_EMULATORS=true` triggering `useAuthEmulator`/
  `useFirestoreEmulator`). If there's no such switch, stop and ask how
  emulator mode is toggled instead of guessing.

## Boot the emulators

Via `/supervised-run` (never bare in your own shell - it must outlive the
driver script):

```
firebase emulators:start --only auth,firestore
```

Reuse an existing supervised entry if one's already running. Ports come from
`firebase.json`, not dynamic - use `"use_dynamic_port": false`.

## Build with the emulator flag baked in

```
fvm flutter build web --dart-define=USE_EMULATORS=true -o build/web-e2e
```

Rebuild whenever app code changes.

## Sign in through the auth-emulator popup relay

`signIn(page, context, email, displayName, postSignInBodyPattern)` in
`references/e2e-helpers.js` drives "Continue with Google" then the relay tab
(`#add-account-button` -> `#email-input` -> `#sign-in`), retrying up to 3
times (the relay popup occasionally fails to load on the first try).
**Requires `headless: false`** - see refs/flutter-web-playwright.md's
headless guidance, this is the one exception.

## Seed and assert state via emulator REST

No app code changes needed:

- Firestore: `http://127.0.0.1:<firestore-port>/v1/projects/<project-id>/databases/(default)/documents/<collection-path>`,
  header `Authorization: Bearer owner` for both reads and writes (any bearer
  token is accepted by the emulator; `owner` is a convention, not a real
  credential). `fetchJson(url, opts)` in the helpers wraps this.
- Auth: `http://127.0.0.1:<auth-port>/emulator/v1/projects/<project-id>/accounts`
  lists/deletes emulator user accounts.
- Pull the signed-in uid out of IndexedDB with `getUidFromIndexedDb(page)`
  (reads `firebaseLocalStorageDb`) instead of scraping it from the UI or
  network log - works against any `firebase_auth` app unmodified.

## Reference

`references/e2e-helpers.js` (next to this file, in the parent `flutter-e2e`
skill) has the full helper module including the emulator-specific functions
above (`signIn`, `fetchJson`, `getUidFromIndexedDb`) alongside the
Firebase-independent driving helpers. Copy it into the target project and
fill in the `CONFIG` block; don't rewrite it from scratch per project.
