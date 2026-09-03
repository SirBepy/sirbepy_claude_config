---
name: flutter-bump
description: Bumps the pinned Flutter stable SDK across the three ZNG repos (zng-app, zng-admin, zng-biller) sequentially via fvm, verifies each with `fvm flutter` analyze/test/build (gated on output text, not exit code), then commits and pushes the bump files per repo (established message style "Bump Flutter to <version>").
disable-model-invocation: true
---

# /flutter-bump

> Bump the Flutter stable SDK pin across zng-app, zng-admin, and zng-biller,
> one repo at a time. **Never run builds for two repos concurrently** — the
> machine overheats. Commit + push per repo is part of the skill (approved by
> Joe 2026-07-28, matching how every prior bump was committed) — but ONLY the
> bump files, only after that repo's verify floor passed, and always via the
> `/commit` skill's rules (pathspec commits, never stage-then-commit).

## Repos (in this order)

1. `C:\Users\tecno\Desktop\Projects\zng-app`
2. `C:\Users\tecno\Desktop\Projects\zng-admin`
3. `C:\Users\tecno\Desktop\Projects\zng-biller`

## 0. Resolve the target version

**This project always uses fvm: only bump to a version fvm itself recognizes
as a stable-channel release.** `fvm install <version>` will happily fetch and
build ANY version string as a raw git ref (log shows `channel [user-branch]`
and a from-source `Building flutter tool...` step) even when that version
isn't a real release yet: found 2026-08-13 with 3.47.0, which Flutter's own
release feed already listed but fvm's release index didn't. That's a
different, unvetted install path, not a normal channel release.

1. Run `fvm releases --channel stable` and read the last row (or the row
   marked `✓`): that's the true target version, fvm's own authoritative
   list.
2. Optionally cross-check against
   `https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json`
   (`current_release.stable` hash → matching `releases` entry's `version`) -
   if it names a newer version than fvm's list does, that version has been
   released but fvm hasn't indexed it yet. Do NOT target it; note the gap in
   the final report instead.

Print the resolved target version before continuing.

## 1. Install once

`fvm install <version>` — one command, run once before the repo loop. fvm's
version cache is global, so this covers all three repos; if already
installed it's a fast no-op.

## 2. Per repo (sequential, never parallel)

For each repo in the order above, complete every step below before moving to
the next repo.

### 2a. Sibling repos only (zng-admin, zng-biller): fetch + pull first

zng-app is skipped here — it may hold in-progress uncommitted work from the
current session, so never fetch or pull it; only the bump-specific files
(`.fvmrc`, `.vscode/settings.json`, `flutter.version`) may be touched there,
and nothing else in zng-app should be disturbed.

For each sibling:
1. `git -C <repo> fetch`
2. `git -C <repo> pull --ff-only` (default branch)

If either command fails for any reason — dirty working tree, non-fast-forward,
detached HEAD, merge conflicts — **skip that repo entirely**: do not run `fvm
use`, do not touch its files, note the skip + reason in the final report, and
move on to the next repo. Never force, never stash, never reset to make the
pull succeed.

### 2b. Already-on-target check

Read the repo's current `flutter.version`. If it already equals the resolved
target version, skip straight to the report as "already on latest" — do not
re-run `fvm use` or the verify steps for that repo.

### 2c. Bump

1. `fvm use <version> --force` inside the repo (updates `.fvmrc` and
   `.vscode/settings.json`, runs `pub get` automatically). `--force` skips an
   interactive version-mismatch prompt this skill never wants to hit.
2. Overwrite `flutter.version` at the repo root with the plain version
   string only — ASCII, no trailing newline, nothing else in the file.
3. **Leave `.vscode/settings.json`'s `dart.flutterSdkPath` exactly as `fvm
   use` wrote it**: the relative `.fvm/versions/<version>`. Never rewrite it
   to an absolute, machine-specific path (a prior version of this skill did;
   Joe rejected that 2026-08-13 as unscalable: hardcoding
   `C:/Users/tecno/...` breaks for every other dev and any CI). This
   knowingly re-accepts the multi-root-workspace risk described in
   `references/fvm-landmines.md`: see Section 3 below for the current
   trade-off and mitigation.
4. **Confirm the pin actually took.** Read `.dart_tool/package_config.json`
   and check its `flutterRoot`:

   ```
   "flutterRoot": "file:///C:/Users/tecno/fvm/versions/<version>"
   ```

   If it points anywhere else (typically `file:///C:/Users/tecno/develop/flutter`,
   a stray global checkout), repair with `fvm flutter pub get`: the PATH bug
   that used to make `fvm flutter` write the wrong `flutterRoot` was fixed
   2026-07-31 (confirmed still holding 2026-08-13 across all three repos
   after repeated `fvm flutter analyze/test/build` calls), so this repair no
   longer needs the pinned binary directly. Re-read `flutterRoot` and confirm
   it now matches before continuing. If it still doesn't, stop this repo and
   report it; do not run 2d, since the verify would be measuring the wrong
   SDK, and say plainly that the PATH fix has regressed.

### 2d. Verify

**This project always uses fvm: run every command as `fvm flutter
<command>`, never the pinned SDK binary directly.** The PATH bug that used to
make `fvm flutter` silently execute the wrong SDK was fixed 2026-07-31; this
skill previously bypassed fvm entirely to route around it, but that's no
longer necessary and contradicts how this project is meant to be used.

1. `fvm flutter analyze`
2. `fvm flutter test`
3. `fvm flutter build web`
4. **zng-app only:** step 3's build carries no `--dart-define-from-file`, so it overwrites the
   shared checkout's `build/web/main.dart.js` with a bundle that targets no API and breaks the
   local e2e harness (`zng-app/e2e/lib/server.js:73`, `assertBundleTargetsConfiguredApi()` reads
   that file from disk unconditionally). Rebuild it for real use: `fvm flutter build web --release
   --dart-define-from-file=.env.local`, then `grep -c 'localhost:3009' build/web/main.dart.js` -
   non-zero or the defines didn't take and the bundle is still broken. Note in the final report
   that `build/web` was rebuilt with local defines. Do not fold this into step 3 itself: the
   `.env.local` file is gitignored and repo-specific, so step 3 stays a portable compile gate that
   works on any machine.

**Gate PASS/FAIL on the command's own output text, never on `$LASTEXITCODE` /
the process exit code.** Confirmed 2026-08-13: `fvm flutter test` returns
exit code 0 even when tests genuinely fail (verified against the pinned
binary directly, which correctly returns 1 for the identical failure), a
distinct fvm bug from the PATH-resolution one, and still open. Read the
output instead:

- `analyze`: PASS = `No issues found!`. Anything else (an issue count, an
  error) = FAIL.
- `test`: PASS = `All tests passed!`. FAIL = `Some tests failed.` (the
  failing test names follow on `Failing tests:`).
- `build web`: PASS = ends with `Built build\web` (Windows) / `Built
  build/web`. A compile error before that line = FAIL.

Record PASS/FAIL for each. On FAIL, capture the last ~20-30 lines of that
command's output for the report.

**Before believing a FAIL, re-check `flutterRoot` (2c step 4).** These commands
run `pub get` themselves when dependencies drift, which can re-point it
mid-verify. A compile error naming an API that genuinely exists in `<version>`
(grep that SDK's own source to confirm) means the resolution broke again, not
that the code is wrong.

### 2e. Commit + push (only if 2d fully passed)

Follow the `/commit` skill's rules (invoke it if not already loaded this
session). Then, per repo:

1. Pathspec commit of ONLY the bump files — never `git add`, never sweep
   other dirty state (zng-app especially may hold unrelated WIP):
   `git -C <repo> commit -m "Bump Flutter to <version>" -- .fvmrc .vscode/settings.json flutter.version`
   Add `pubspec.lock` to the pathspec only when the bump itself changed it
   (SDK-pinned packages: meta, test_api, matcher).
2. `git -C <repo> push`

Message is always exactly `Bump Flutter to <version>` — the established
style used by every prior bump commit in all three repos. No prefixes.

If ANY of analyze/test/build FAILED for this repo: do NOT commit or push it.
Leave its tree dirty, report the failure, and continue to the next repo.

## 3. Multi-root workspace file - no longer touched by this skill

`C:\Users\tecno\Desktop\Projects\zng-admin.code-workspace` bundles all four
repos (`zng-api`, `zng-admin`, `zng-app`, `zng-biller`) as one VS Code
multi-root workspace. A *relative* `dart.flutterSdkPath` resolves against the
directory containing the open `.code-workspace` FILE, not the individual
workspace folder it's set in, whenever this workspace is open - full
root-cause detail (Dart-Code's `extension.js` internals) is in
`references/fvm-landmines.md`. That can make Dart-Code silently fall back to
whatever Flutter is on PATH when the repo is opened through this workspace
file specifically.

This skill previously wrote an absolute `dart.flutterSdkPath` into the
workspace file's `settings` block to neutralize that. **Joe rejected the
absolute-path approach entirely 2026-08-13** (not scalable: hardcodes a
single machine's home directory), so this skill no longer edits the
workspace file at all, and the multi-root-workspace risk above is a known,
accepted trade-off, not something this skill fixes. If in-editor analysis
inside the multi-root workspace ever looks stale or wrong, that's the likely
cause: reload the window first; if that doesn't help, it may need a one-off
manual `dart.flutterSdkPath` set in the workspace file (or opening the repo
standalone instead of through the workspace), but that's a manual call for
Joe, not something this skill does automatically.

## fvm reliability notes

Full post-mortem (two stacked fvm bugs, consequences, PATH root cause) is in
`references/fvm-landmines.md`. Current state:

- **PATH-resolution bug (fvm silently running the wrong SDK): fixed
  2026-07-31.** `fvm flutter <command>` is safe for real work now, confirmed
  again 2026-08-13 (`flutterRoot` stayed correct across all three repos
  through repeated `fvm flutter analyze/test/build` calls). This skill uses
  `fvm flutter` throughout: do not reintroduce the direct-pinned-binary
  bypass without new evidence the PATH bug regressed.
- **Exit-code bug (open, found 2026-08-13):** `fvm flutter test` returns exit
  code 0 even on genuine test failures. 2d gates on output text specifically
  because of this: never trust `$LASTEXITCODE` from an `fvm flutter` call.
- Always verify `flutterRoot` in `.dart_tool/package_config.json` after
  `fvm use` (2c step 4) — a correctly symlinked `.fvm/flutter_sdk` and a
  correct `fvm flutter --version` both prove nothing; only `flutterRoot` does.
- Use the relative `dart.flutterSdkPath` `fvm use` writes natively (2c step
  3): never an absolute, machine-specific path.

Whenever a bump changes the version, after step 2 of the per-repo loop
completes for all three repos, also run `fvm global <version>` once
(matching whichever version they landed on, only if all three genuinely
landed on it, a skipped or failed repo breaks the match) to keep
`fvm\default`, and therefore PATH, pointed at the current pin. Mention in
the final report whether this ran or was skipped (and why).

## fvm quirks (not failures)

- After `fvm use` changes the pinned SDK, VS Code's Dart/Flutter language
  server keeps analyzing against the old SDK until the window is reloaded
  (Command Palette → "Developer: Reload Window", or restart VS Code).
  Mention this once in the final report, not per repo.

## Final report

For each of the 3 repos, report:

- **zng-app**: bumped `<old>` → `<new>` (or "already on `<new>`"), then
  analyze/test/build PASS or FAIL with an output tail for any FAIL, then
  whether the local-defines rebuild (2d step 4) ran and its grep count.
- **zng-admin**: fetch/pull result; if skipped, the reason; otherwise same
  bump + verify detail as above.
- **zng-biller**: same as zng-admin.

Then: whether `fvm global <version>` ran to keep the PATH alias current, or
was skipped and why (a skipped/failed repo breaks the "all three landed on
it" match).

Then:

- Reminder: reload the VS Code window (Dart/Flutter language server) before
  trusting in-editor analysis.
- Whether any repo needed the `flutterRoot` repair in 2c step 4, and whether
  the `Can't load Kernel binary` warning fired: this is now a known
  benign-but-persistent quirk (fires on nearly every `fvm` invocation, does
  not affect command results) rather than an automatic "fvm is broken, needs
  reinstalling" signal; only escalate that if `flutterRoot` itself came
  back wrong or a repair didn't hold.
- Per repo: the commit sha + push result, or "not committed — verify failed"
  with the failing check named.
