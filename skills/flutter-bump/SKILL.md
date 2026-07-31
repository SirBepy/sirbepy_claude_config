---
name: flutter-bump
description: Triggers on /flutter-bump only. Bumps the pinned Flutter stable SDK across the three ZNG repos (zng-app, zng-admin, zng-biller) sequentially via fvm, verifies each with analyze/test/build, then commits and pushes the bump files per repo (established message style "Bump Flutter to <version>").
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

Fetch `https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json`.
`current_release.stable` is a hash — find the entry in `releases` whose `hash`
matches it (or, if that fails, the first entry with `channel: "stable"`) and
read its `version`. If the fetch or parse fails, fall back to `fvm releases
--channel stable` and take the latest listed stable version.

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

1. `fvm use <version>` inside the repo (updates `.fvmrc` and
   `.vscode/settings.json`, runs `pub get` automatically).
2. Overwrite `flutter.version` at the repo root with the plain version
   string only — ASCII, no trailing newline, nothing else in the file.
3. **Confirm the pin actually took (mandatory — see "fvm falls back silently"
   below).** Read `.dart_tool/package_config.json` and check its `flutterRoot`:

   ```
   "flutterRoot": "file:///C:/Users/tecno/fvm/versions/<version>"
   ```

   If it points anywhere else (typically `file:///C:/Users/tecno/develop/flutter`,
   a stray global checkout), repair it with the pinned SDK's own binary — NOT
   with `fvm`, which is what wrote the wrong value:

   `& "C:\Users\tecno\fvm\versions\<version>\bin\flutter.bat" pub get`

   Re-read `flutterRoot` and confirm it now matches before continuing. If it
   still doesn't, stop this repo and report it — do not run 2d, since the
   verify would be measuring the wrong SDK.

### 2d. Verify

Run each as its own command (never chained with `&&`/`;`/`|`), from the repo
root. Call the **pinned SDK's binary directly**, never `fvm flutter` — the
whole point of this step is proving the code is valid under `<version>`, and
`fvm flutter` can silently execute a different SDK (see below), which would
make every PASS meaningless:

1. `& "C:\Users\tecno\fvm\versions\<version>\bin\flutter.bat" analyze`
2. `& "C:\Users\tecno\fvm\versions\<version>\bin\flutter.bat" test`
3. `& "C:\Users\tecno\fvm\versions\<version>\bin\flutter.bat" build web`

Record PASS/FAIL for each. On FAIL, capture the last ~20-30 lines of that
command's output for the report.

**Before believing a FAIL, re-check `flutterRoot` (2c step 3).** These commands
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

## fvm falls back silently — do not trust `fvm flutter`

`Can't load Kernel binary: Invalid kernel binary format version (expected N,
found M)` on an `fvm` invocation is **not harmless**, and an earlier version of
this skill wrongly said it was. It means fvm's own Dart snapshot can't run, so
fvm falls through to whatever `flutter` is on PATH — on this machine
`C:\Users\tecno\develop\flutter` (3.38.3 as of 2026-07-29), not the pin.

Consequences, all of which have actually happened:

- `fvm flutter pub get` writes the WRONG `flutterRoot`, so running it to "fix"
  the resolution re-breaks it every time. Hence 2c step 3's direct-binary repair.
- `fvm flutter analyze/test/build` would verify the bump against the old SDK
  and report a meaningless PASS. Hence 2d's direct-binary commands.
- A running `flutter run` dev server compiles through `package_config.json`, so
  a wrong `flutterRoot` makes every hot restart fail to recompile while the
  browser keeps serving the last good build — edits look like no-ops.

`.fvm/flutter_sdk` symlinking correctly, and `fvm flutter --version` printing
the right number, both prove nothing. Only `flutterRoot` does.

If this fires during a bump, flag it in the final report as a machine-level
issue: fvm's snapshot needs reinstalling, and until it is, every session pays
this tax.

## fvm quirks (not failures)

- After `fvm use` changes the pinned SDK, VS Code's Dart/Flutter language
  server keeps analyzing against the old SDK until the window is reloaded
  (Command Palette → "Developer: Reload Window", or restart VS Code).
  Mention this once in the final report, not per repo.

## Final report

For each of the 3 repos, report:

- **zng-app**: bumped `<old>` → `<new>` (or "already on `<new>`"), then
  analyze/test/build PASS or FAIL with an output tail for any FAIL.
- **zng-admin**: fetch/pull result; if skipped, the reason; otherwise same
  bump + verify detail as above.
- **zng-biller**: same as zng-admin.

Then:

- Reminder: reload the VS Code window (Dart/Flutter language server) before
  trusting in-editor analysis.
- Whether any repo needed the `flutterRoot` repair in 2c step 3, and whether
  the `Can't load Kernel binary` fallback fired — if either did, say plainly
  that fvm is broken on this machine and needs reinstalling.
- Per repo: the commit sha + push result, or "not committed — verify failed"
  with the failing check named.
