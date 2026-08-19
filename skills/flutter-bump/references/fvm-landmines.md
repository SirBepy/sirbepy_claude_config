# fvm landmines — post-mortem detail

Background/investigation detail for the operative rules in SKILL.md's "2c
Bump" and "fvm falls back silently" sections. Not needed to run the skill —
read only if something's misbehaving and you want the why.

## Multi-root workspace: relative flutterSdkPath resolves against the wrong directory

Confirmed root cause 2026-07-31 (traced through Dart-Code's own
`extension.js`): its `resolvePaths()` helper resolves a *relative*
`dart.flutterSdkPath` against the directory containing the open
**`.code-workspace` file itself**, not the individual workspace folder the
setting is defined in, whenever one is open:

```js
const relativePathBase = vscode.workspace.workspaceFile?.scheme === "file"
    ? path.dirname(fsPath(vscode.workspace.workspaceFile))   // Desktop\Projects, not the repo!
    : vscode.workspace.workspaceFolders?.length
        ? fsPath(vscode.workspace.workspaceFolders[0].uri)
        : undefined;
```

Every repo's `.vscode/settings.json` holds the *relative* value `fvm use`
writes (`.fvm/versions/<version>`). Opened standalone, that resolves fine
(the fallback branch just uses the one workspace folder). Opened through
`zng-admin.code-workspace`, it resolves against `Desktop\Projects` instead —
`Desktop\Projects\.fvm\versions\<version>` doesn't exist — so Dart-Code
silently falls through to whatever Flutter is on system PATH (the stale
global install), producing real compile errors in the editor for APIs the
pinned version genuinely has. 2c step 3 neutralizes this per-repo by writing
an absolute path instead; section 3's workspace-level write is the same fix
at the workspace level, since a genuinely correct absolute path there is a
reliable backstop regardless of which folder's settings the analyzer ends up
consulting.

Confirmed 2026-07-31: after the workspace-level edit, opening the multi-root
workspace still required one manual `pub get` inside it (Command Palette →
"Dart: Get Packages", or run it in any repo's terminal) before Dart-Code
picked up the corrected SDK — a plain reload/restart wasn't enough on its
own.

## Two distinct fvm bugs (confirmed 2026-07-31) — fixing one does not fix the other

1. **fvm's own Dart snapshot going stale.** `Can't load Kernel binary: Invalid
   kernel binary format version (expected N, found M)` means fvm's globally
   activated snapshot was built by a different Dart VM than whatever `dart`
   is currently first on PATH. Fix: `dart pub global activate fvm` (rebuilds
   the snapshot against the current PATH dart). This only silences the
   warning — it does NOT fix bug 2 below, which was mistakenly assumed fixed
   the first time this happened.

   **2026-08-13: found fvm's CLI entirely missing** (`dart pub global list`
   empty, no `fvm.exe`/`fvm.bat` anywhere, not in winget), a more severe
   version of this, not just a stale snapshot. Reinstalled via `dart pub
   global activate fvm` (same fix as above). The warning still fired on
   every single subsequent `fvm` command for the rest of the session despite
   the fresh install; it did not actually silence it this time. It appears
   harmless in practice (every command's real output/exit behavior, aside
   from bug 3 below, was correct regardless), so treat it as persistent
   background noise rather than a signal something is broken, unless paired
   with an actual wrong result (`flutterRoot` mismatch, missing release
   list, etc.).
2. **`fvm flutter <command>` misresolving for real operations even with a
   healthy snapshot.** `fvm flutter --version` prints the right number
   regardless — it proves nothing, likely just echoing cached config. Real
   commands (`pub get` above all) can still silently execute against
   whatever plain `flutter` resolves to on PATH instead of the project's
   pin, rewriting `.dart_tool/package_config.json`'s `flutterRoot` to the
   wrong SDK. Caught live: reactivating fvm (bug 1's fix) did NOT stop a
   subsequent `fvm flutter pub get` from re-corrupting zng-app's
   `flutterRoot` back to the stale global SDK.

Consequences, while bug 2 was active (pre-2026-07-31, and the reason the
skill bypassed fvm entirely for verify/repair until the 2026-08-13
re-confirmation above):

- `fvm flutter pub get` wrote the WRONG `flutterRoot`, so running it to "fix"
  the resolution re-broke it every time. Repair had to go through the pinned
  binary directly instead.
- `fvm flutter analyze/test/build` would verify the bump against the old SDK
  and report a meaningless PASS. Verify had to go through the pinned binary
  directly instead.
- A running `flutter run` dev server compiles through `package_config.json`, so
  a wrong `flutterRoot` makes every hot restart fail to recompile while the
  browser keeps serving the last good build — edits look like no-ops.

Now that bug 2 is confirmed fixed, none of the above apply; `fvm flutter`
is safe for all of this again, but if `flutterRoot` is ever found wrong
after an `fvm flutter` call, this is the failure mode to suspect first.

`.fvm/flutter_sdk` symlinking correctly, and `fvm flutter --version` printing
the right number, both prove nothing. Only `flutterRoot` does.

**Root cause of why bug 2 kept recurring, and the actual fix (applied
2026-07-31):** `C:\Users\tecno\develop\flutter` — an ancient, unrelated global
Flutter install — sat first on the User `PATH`, so ANY bare `flutter`/`dart`
command anywhere (a stray terminal command, a VS Code background task,
muscle memory) would resolve there instead of any project's pin. Permanent
fix applied: ran `fvm global <version>` (creates/updates the
`C:\Users\tecno\fvm\default` symlink) and replaced the `develop\flutter\bin`
entry in User `PATH` with `C:\Users\tecno\fvm\default\bin`. Takes effect in
new terminals/processes only — sessions already running keep their inherited
(stale) PATH. This is why the skill still runs `fvm global <version>` after
every bump: to keep the alias pointed at the current pin even though the
PATH-ordering bug itself is fixed.

**Reconfirmed fixed 2026-08-13:** re-verified `flutterRoot` in all three
repos (zng-app, zng-admin, zng-biller) after running `fvm flutter
analyze`/`test`/`build web` through each: every one stayed correctly
pointed at the pinned SDK. The skill switched back to running everything via
`fvm flutter` (Joe: "this project ALWAYS uses fvm") on the strength of this
check; if `flutterRoot` ever comes back wrong again, treat bug 2 as
regressed and fall back to the pinned-binary bypass until it's re-fixed.

## Bug 3 (found 2026-08-13, still open): `fvm flutter test` swallows the exit code

`fvm flutter test` returns exit code 0 even when the run genuinely failed.
Confirmed directly: the identical failing test (`test/widget_test.dart`'s
stale default counter smoke test in zng-app) returned `$LASTEXITCODE 0`
through `fvm flutter test` but `1` through the pinned binary
(`flutter.bat test`) called directly, same repo, same SDK version, back to
back. `fvm flutter analyze` and `fvm flutter build web` were not confirmed to
have the same issue (their failure text is easy to distinguish either way),
but treat any `fvm flutter <command>`'s exit code as untrustworthy on
principle: read the command's own stdout for the real pass/fail signal
instead (see SKILL.md 2d for the specific markers).

## Absolute `dart.flutterSdkPath` workaround - retired 2026-08-13

The multi-root-workspace bug above (relative path resolving against the
`.code-workspace` file's directory) is still real and still unfixed at the
Dart-Code level. This skill used to work around it by writing an absolute,
machine-specific `dart.flutterSdkPath` both per-repo (old 2c step 3) and at
the workspace level (old Section 3). Joe rejected that approach 2026-08-13:
hardcoding `C:/Users/tecno/...` isn't portable to another dev's machine or
to CI. The skill now leaves `dart.flutterSdkPath` as the relative value `fvm
use` writes everywhere, and no longer touches the workspace file at all.
The multi-root-workspace risk is a knowingly accepted trade-off now, not a
solved problem: if it bites, the fix is a manual one-off, not something
this skill automates.
