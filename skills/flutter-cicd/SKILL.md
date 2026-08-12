---
name: flutter-cicd
description: Scaffolds an Android release pipeline for a Flutter project - generates a signing keystore, wires build.gradle, adds a GitHub Actions workflow that builds a signed APK and publishes a versioned GitHub Release, optionally uploads an AAB to the Google Play internal track, optionally deploys the Flutter web build to GitHub Pages, and sets the repo secrets. Handles single-app repos and melos monorepos.
disable-model-invocation: true
---

# /flutter-cicd

> Give a Flutter app a working Android release pipeline: signed APK on every push to main, published as a versioned GitHub Release for sideloading. Optionally wires the launcher icon too.

This is the gate-free, reusable version of what was first built by hand for `pomalo`. Baseline target is **APK -> GitHub Releases** (free, instant, no Play account). **Play Store upload (AAB -> internal track) is an optional bolt-on** in Step 7 that layers onto the same workflow and the same keystore - it stays dormant until the Play secret exists, so it is safe to wire before the dev has paid for a Play account.

## Preconditions (check first, don't assume)

Run these and report what's missing before touching anything:

- `git remote -v` -> repo has a GitHub `origin`. If not, stop and ask.
- `.fvmrc` -> note the Flutter version (used to pin the workflow). If absent, read `flutter --version`.
- `keytool` on PATH (ships with any JDK). On Windows it's usually under `Eclipse Adoptium/jdk-*/bin/keytool`.
- `gh --version` + `gh auth status` -> needed to set secrets.
- Detect layout:
  - **Single app**: `pubspec.yaml` + `android/` at repo root.
  - **Melos monorepo**: `melos.yaml` at root, apps under `apps/*/` each with their own `pubspec.yaml` + `android/`. Ask (AskUserQuestion) **which app(s)** to set up; repeat the per-app steps for each. Paths below become `apps/<app>/...` and the workflow `cd`s into the app dir before building.

## Step 1 - Launcher icon (optional, ask first)

Ask `[UX]` whether to set up the icon now. If yes and no source image exists, ask for a square >=1024px PNG (or an SVG you can rasterize via headless Chrome: wrap the SVG in an HTML at 1024x1024, `chrome --headless=new --default-background-color=00000000 --screenshot`).

Add to `dev_dependencies`: `flutter_launcher_icons: ^0.14.4` (verified publisher `fluttercommunity.dev`). Add config block to `pubspec.yaml`:

```yaml
flutter_launcher_icons:
  android: true
  ios: false # set true only if an ios/ runner scaffold exists, else the tool crashes
  image_path: "assets/icon/icon.png"
  min_sdk_android: 21
  adaptive_icon_background: "assets/icon/icon_bg.png"   # solid hex color also allowed
  adaptive_icon_foreground: "assets/icon/icon_fg.png"   # snail/mark padded on transparent
  web:
    generate: true
    image_path: "assets/icon/icon.png"
```

Run `fvm flutter pub get` then `fvm dart run flutter_launcher_icons`. The `assets/icon/` sources are build inputs only - do NOT list them under `flutter: assets:` (keeps them out of the bundle).

## Step 2 - Release keystore (generated OUTSIDE the repo)

Never commit a keystore or its password. Generate once, store under `~/.android-keystores/`. Run as
separate PowerShell calls (no `;`/`&&` chaining):

```powershell
$KsDir = "$env:USERPROFILE\.android-keystores"
New-Item -ItemType Directory -Force -Path $KsDir | Out-Null
$Ks = "$KsDir\<app>-release.jks"
```
```powershell
$Bytes = New-Object byte[] 24
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
$Pass = ([Convert]::ToBase64String($Bytes) -replace '[/+=]', '').Substring(0, 28)
```
```powershell
# Windows PowerShell 5.1 prepends a UTF-8 BOM to Set-Content/Out-File even with
# -Encoding utf8, which later breaks gh secret set - WriteAllText with a no-BOM
# encoding avoids it.
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$KsDir\<app>-release.pass.txt", $Pass, $Utf8NoBom)
```
```powershell
keytool -genkeypair -v -keystore $Ks -storetype JKS -keyalg RSA -keysize 2048 `
  -validity 10000 -alias <app> -storepass $Pass -keypass $Pass `
  -dname "CN=<App>, OU=SirBepy, O=SirBepy, L=Zagreb, S=Zagreb, C=HR"
```

This matches the original bash algorithm exactly: 24 random bytes, base64-encoded, `/+=`
stripped, truncated to 28 chars.

If the keystore already exists, reuse it - do NOT regenerate (a new key breaks upgrade-in-place for anyone who already installed).

Write `android/key.properties` (gitignored) for LOCAL release builds:

```properties
storeFile=<absolute path to the .jks, forward slashes on Windows>
storePassword=<PASS>
keyAlias=<app>
keyPassword=<PASS>
```

Add to `.gitignore`:

```
android/key.properties
*.jks
*.keystore
```

## Step 3 - Wire android/app/build.gradle.kts

Read local `key.properties` for dev, fall back to CI env vars, and fall back to debug keys if neither exists (so `flutter run --release` still works with no keystore). At the top of the file (above `plugins {}` or just after):

```kotlin
import java.util.Properties
import java.io.FileInputStream
```

After the `plugins {}` block:

```kotlin
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}
fun signingValue(propKey: String, envKey: String): String? =
    keystoreProperties.getProperty(propKey) ?: System.getenv(envKey)
val releaseStoreFile: String? = signingValue("storeFile", "RELEASE_STORE_FILE")
val hasReleaseSigning: Boolean = releaseStoreFile != null && file(releaseStoreFile).exists()
```

Inside `android {}` add a `signingConfigs` block and point `release` at it:

```kotlin
    signingConfigs {
        create("release") {
            if (hasReleaseSigning) {
                storeFile = file(releaseStoreFile!!)
                storePassword = signingValue("storePassword", "RELEASE_STORE_PASSWORD")
                keyAlias = signingValue("keyAlias", "RELEASE_KEY_ALIAS")
                keyPassword = signingValue("keyPassword", "RELEASE_KEY_PASSWORD")
            }
        }
    }
    buildTypes {
        release {
            signingConfig = if (hasReleaseSigning)
                signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }
```

**Common gotcha - core library desugaring.** If the app uses `flutter_local_notifications` (or anything needing `java.time` backports), the release build fails with *"requires core library desugaring to be enabled"*. Fix: set `isCoreLibraryDesugaringEnabled = true` in `compileOptions {}` and add
`coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")` to a `dependencies {}` block at the end of the file.

## Step 4 - GitHub Actions workflow

Write `.github/workflows/build.yml` (for a monorepo app, add `cd apps/<app>` before the flutter commands and adjust the APK path / working-directory). Template:

```yaml
name: Build APK
on:
  push:
    branches: [ main ]
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '17' }
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '<from .fvmrc>'  # keep in sync with .fvmrc
          channel: stable
          cache: true
      - run: flutter pub get
      - name: Decode release keystore
        env:
          RELEASE_KEYSTORE_BASE64: ${{ secrets.RELEASE_KEYSTORE_BASE64 }}
        run: |
          if [ -n "$RELEASE_KEYSTORE_BASE64" ]; then
            echo "$RELEASE_KEYSTORE_BASE64" | base64 -d > "$RUNNER_TEMP/release.jks"
            echo "RELEASE_STORE_FILE=$RUNNER_TEMP/release.jks" >> "$GITHUB_ENV"
          else
            echo "::warning::No RELEASE_KEYSTORE_BASE64 secret; release will be debug-signed."
          fi
      - id: version
        run: |
          VERSION=$(grep -m1 '^version:' pubspec.yaml | sed -E 's/version:\s*([^+]+).*/\1/' | tr -d '[:space:]')
          echo "name=$VERSION" >> "$GITHUB_OUTPUT"
      # versionCode from the CI run number, NOT pubspec's "+N" - see "versionCode" below.
      - name: Build release APK
        env:
          RELEASE_STORE_PASSWORD: ${{ secrets.RELEASE_STORE_PASSWORD }}
          RELEASE_KEY_ALIAS: ${{ secrets.RELEASE_KEY_ALIAS }}
          RELEASE_KEY_PASSWORD: ${{ secrets.RELEASE_KEY_PASSWORD }}
        run: flutter build apk --release --build-number=${{ github.run_number }}
      - run: cp build/app/outputs/flutter-apk/app-release.apk <app>.apk
      - uses: softprops/action-gh-release@v2
        with:
          tag_name: v${{ steps.version.outputs.name }}
          name: v${{ steps.version.outputs.name }}
          body: Auto-built release APK. Sideload on your phone (enable "install unknown apps").
          files: <app>.apk
          make_latest: true
```

Note: the tag is the pubspec version (e.g. `v1.0.0`). Re-pushing without bumping `version:` updates the same release rather than making a new one - bump `version:` in pubspec for a fresh tag.

**versionCode.** Always pass `--build-number=${{ github.run_number }}` rather than letting pubspec's `+N` supply it. Play permanently burns every versionCode it accepts and rejects a repeat, so the number has to increase on every upload with no human in the loop; `run_number` is monotonic per repo and free. The version *name* still comes from pubspec, so the GitHub Release tag is unaffected. Do this even on APK-only projects - it costs nothing and means Step 7 can be bolted on later without a versioning migration. (Date-based `YYMMDDHHmm` is the alternative if the repo may move CI hosts and reset `run_number`.)

## Step 5 - Set repo secrets

`gh secret set --body` takes the value as a CLI argument (not stdin), so no pipe chain and no
file-write BOM risk. Each secret as its own separate PowerShell call:

```powershell
$Repo = "<owner/repo>"
$KsB64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($Ks))
gh secret set RELEASE_KEYSTORE_BASE64 --repo $Repo --body $KsB64
```
```powershell
gh secret set RELEASE_STORE_PASSWORD --repo $Repo --body $Pass
```
```powershell
gh secret set RELEASE_KEY_ALIAS --repo $Repo --body "<app>"
```
```powershell
gh secret set RELEASE_KEY_PASSWORD --repo $Repo --body $Pass
```
```powershell
gh secret list --repo $Repo
```

`[Convert]::ToBase64String` produces unwrapped base64 (no line breaks), matching bash's `base64 -w0`.

`gh secret set` needs the account hook to have switched to the repo's owner - warn the dev if a credential popup appears (it came from Claude).

## Step 6 - Verify locally, then commit

- Build once locally: `fvm flutter build apk --release`. Confirm it's signed with the release cert, not debug:
  `apksigner verify --print-certs <apk>` -> `Signer #1 certificate DN: CN=<App>...` (NOT `CN=Android Debug`).
- Run the project's fast floor: `fvm flutter analyze` + `fvm flutter test`.
- Invoke `/commit`, which commits by pathspec - do not pre-stage. Pushing to `main` is what first runs the pipeline and publishes the release - treat that push as an outward-facing action and confirm with the dev before pushing.

## Web hosting - GitHub Pages (optional, ask first)

Ask `[UX]` whether to set up web hosting via GitHub Pages. Flutter web compiles to static files, so Pages serves it fine - default for the portfolio (uniform across static-HTML and Flutter projects, free, no per-app cloud project). If yes, read `references/gh-pages.md` for the blocker check, routing/base-href rules, and the `deploy-web.yml` workflow.

## Step 7 - Play Store upload (optional, ask first)

Ask `[TOOLING]` whether to wire Play now. **Wiring it is safe even with no Play account** - the steps are gated on a secret that does not exist yet, so they no-op until the dev sets it. Prefer wiring it dormant over leaving it undone. If yes, read `references/play-store.md` for the manual prerequisites checklist, the service-account secret, and the workflow steps to append to Step 4's job.

## Apple / TestFlight

Out of scope here - $99/yr, needs a Mac or a paid macOS runner. `/ios-run` covers the manual build path.
