<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard flagged done/243-flutter-bump-resolve-workspace-write-contradiction.md, which is about writing dart.flutterSdkPath into zng-admin.code-workspace and was already resolved 2026-08-13. Different surface entirely; shares only the words "flutter", "bump", "step". -->
# /flutter-bump's `build web` verify step leaves zng-app's build/web unusable for local e2e

**Type:** skill-improvement
**Origin:** ai

## Goal

`/flutter-bump` should not leave `zng-app/build/web` in a state that breaks the local e2e harness
and hand-testing. Its final `build web` in zng-app must carry the local env defines, or the skill
must say plainly that it destroyed the bundle and who needs to rebuild it.

## Context

Skill file: `C:\Users\tecno\.claude-personal\skills\flutter-bump\SKILL.md`, section **2d. Verify**,
step 3 (`fvm flutter build web`).

Incident 2026-09-02, bumping 3.47.1 -> 3.47.2. The verify step ran a bare `fvm flutter build web`
in `C:\Users\tecno\Desktop\Projects\zng-app`. That overwrites the shared checkout's
`build/web/main.dart.js` with a bundle built with NO `--dart-define-from-file`, so it points at no
API at all.

Measured on the resulting artifact (4736800 bytes, 18:00:35):

- `grep -c 'localhost:3009' build/web/main.dart.js` -> 0
- `grep -c 'api.dev.ng.zirtue.com' build/web/main.dart.js` -> 0

A concurrent Conductor session (`0e07`) had an e2e suite in flight and it crashed with
`build/web targets <none> but the suite is configured for http://localhost:3009/api/core`. That
session initially misattributed the breakage to a third session before tracing it to the bump.

The rejecting guard is `zng-app/e2e/lib/server.js:73`: `ensureServer` calls
`assertBundleTargetsConfiguredApi()` unconditionally, BEFORE the `isListening` check, and that
function reads `build/web/main.dart.js` from disk regardless of `E2E_APP_URL`. Verified by reading
the file this session. (That guard's own read-from-disk bug is a zng-app concern, not this todo's.)

The documented local build shape is at `zng-app/e2e/README.md:118-128`:
`flutter build web --release --dart-define-from-file=.env.local`.

Manual fix applied at the time: rebuilt with that command, giving 4737169 bytes and 6 grep hits for
`localhost:3009`. Cost roughly 90 extra seconds and only happened because the peer session
reported it. Nothing in the skill would have caught it.

Only zng-app has an e2e harness reading `build/web`. zng-admin and zng-biller are unaffected, so
this is a zng-app-specific step, not a change to the shared verify loop.

## Approach

In `SKILL.md` section 2d, add a zng-app-only step after step 3:

1. Keep the plain `fvm flutter build web` as the verify gate (it is the compile check, and its
   PASS text `Built build\web` is what 2d reads).
2. Then, in zng-app only, rebuild the bundle for real use:
   `fvm flutter build web --release --dart-define-from-file=.env.local`.
3. Assert the result carries the defines before calling the repo done:
   `grep -c 'localhost:3009' build/web/main.dart.js` must be non-zero. A 0 here means the defines
   did not take and the bundle is still broken.
4. Note in the final report that `build/web` was rebuilt with local defines, so a peer session
   reading the tree knows the artifact changed and why.

Alternative considered and rejected: making step 3 itself pass `--dart-define-from-file=.env.local`
and skipping the second build. Rejected because the file is gitignored and repo-specific, so the
verify gate would fail in any repo or machine lacking it, turning a portable compile check into a
local-env-dependent one. Two builds is ~90s and keeps the gate portable.

Also worth folding in: the skill should note that a bump in a SHARED checkout mutates `build/web`
and the `.fvm/flutter_sdk` symlink under any concurrent session, and tell the operator to
`post_message` before the first build rather than after. In this incident the peer had already
crashed by the time the bump session announced itself.

## Acceptance

- Running `/flutter-bump` end to end leaves `zng-app/build/web/main.dart.js` with a non-zero grep
  count for `localhost:3009`.
- Booting the e2e harness against the main tree passes `assertBundleTargetsConfiguredApi()` instead
  of erroring with `build/web targets <none>`.
- The bare `fvm flutter build web` compile gate still runs and is still what 2d's PASS/FAIL reads,
  so a genuine compile break under the new SDK still fails the repo.
- zng-admin and zng-biller verify steps are unchanged.

## Notes

Do not add this to the zng-app project backlog. The defect is in the global skill, and per
`CLAUDE.md`'s AI-todos section a finding about the `~/.claude` tree belongs in this repo's own
backlog, which is where this file sits.

Related but separate, and NOT this todo: `zng-app/e2e/lib/server.js:73` validating `build/web` from
disk even when `E2E_APP_URL` points elsewhere. It can also pass while a different bundle is served,
which is the more dangerous direction. Session `0e07` found it and owns it; file it in zng-app's
backlog if it is still unfiled.
