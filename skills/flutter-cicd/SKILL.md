---
name: flutter-cicd
description: Triggers on /flutter-cicd only. Scaffolds an Android release pipeline for a Flutter project - generates a signing keystore, wires build.gradle, adds a GitHub Actions workflow that builds a signed APK and publishes a versioned GitHub Release, optionally uploads an AAB to the Google Play internal track, and sets the repo secrets. Handles single-app repos and melos monorepos.
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

Ask `[UX]` whether to set up the icon now. If yes and no source image exists, ask for a square >=1024px PNG (or an SVG you can rasterize via headless Chrome - see the pomalo `render_icons.cjs` pattern: wrap the SVG in an HTML at 1024x1024, `chrome --headless=new --default-background-color=00000000 --screenshot`).

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

Never commit a keystore or its password. Generate once, store under `~/.android-keystores/`:

```bash
KS_DIR="$HOME/.android-keystores"; mkdir -p "$KS_DIR"
KS="$KS_DIR/<app>-release.jks"
PASS=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 28)
echo "$PASS" > "$KS_DIR/<app>-release.pass.txt"
keytool -genkeypair -v -keystore "$KS" -storetype JKS -keyalg RSA -keysize 2048 \
  -validity 10000 -alias <app> -storepass "$PASS" -keypass "$PASS" \
  -dname "CN=<App>, OU=SirBepy, O=SirBepy, L=Zagreb, S=Zagreb, C=HR"
```

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

```bash
REPO=<owner/repo>
base64 -w0 "$KS" | gh secret set RELEASE_KEYSTORE_BASE64 --repo "$REPO"
printf '%s' "$PASS"  | gh secret set RELEASE_STORE_PASSWORD --repo "$REPO"
printf '%s' "<app>"  | gh secret set RELEASE_KEY_ALIAS      --repo "$REPO"
printf '%s' "$PASS"  | gh secret set RELEASE_KEY_PASSWORD   --repo "$REPO"
gh secret list --repo "$REPO"
```

`gh secret set` on stdin needs the account hook to have switched to the repo's owner - warn the dev if a credential popup appears (it came from Claude).

## Step 6 - Verify locally, then commit

- Build once locally: `fvm flutter build apk --release`. Confirm it's signed with the release cert, not debug:
  `apksigner verify --print-certs <apk>` -> `Signer #1 certificate DN: CN=<App>...` (NOT `CN=Android Debug`).
- Run the project's fast floor: `fvm flutter analyze` + `fvm flutter test`.
- Stage everything, then invoke `/commit` (never commit directly). Pushing to `main` is what first runs the pipeline and publishes the release - treat that push as an outward-facing action and confirm with the dev before pushing.

## Web hosting - GitHub Pages (optional, ask first)

Flutter web compiles to static files, so GitHub Pages serves it fine. Default for the portfolio (uniform across static-HTML and Flutter projects, free, no per-app cloud project).

**Blocker check first:** `gh repo view <owner/repo> --json visibility`. Pages does NOT publish from a **private** repo on the Free plan - it needs the repo public or GitHub Pro. If private + Free, ask the dev: make public, or use Firebase Hosting instead (ignores repo visibility). Before making a repo public, run a secrets pre-flight over the working tree AND git history (`git log --all --name-only` for keystores/service-account JSON/.env; grep for private keys/tokens). Firebase API keys in `firebase_options.dart` / `google-services.json` are public-safe by design.

**Routing:** Flutter web defaults to **hash** URLs (refresh-safe on Pages) unless the app calls `usePathUrlStrategy()`. If it uses path strategy, add a `404.html` = copy of `index.html` fallback.

**base-href:** a project page lives at `<user>.github.io/<repo>/`, so build with `--base-href /<repo>/`. A root/user site (`<user>.github.io`) needs no base-href.

Workflow `.github/workflows/deploy-web.yml`:

```yaml
name: Deploy Web (GitHub Pages)
on:
  push: { branches: [ main ] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
concurrency: { group: pages, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with: { flutter-version: '<from .fvmrc>', channel: stable, cache: true }
      - run: flutter pub get
      - run: flutter build web --release --base-href /<repo>/
      - uses: actions/upload-pages-artifact@v3
        with: { path: build/web }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Enable Pages with Actions as the source (once): `gh api -X POST repos/<owner/repo>/pages -f build_type=workflow`.

**Firebase apps - one manual step:** if the app uses Firebase Auth (Google popup via `signInWithPopup`), add the hosting domain (e.g. `<user>.github.io`) to Firebase Console -> Authentication -> Settings -> Authorized domains, or sign-in popups are rejected. This is one-time and covers all project pages on that github.io domain.

## Step 7 - Play Store upload (optional, ask first)

Ask `[TOOLING]` whether to wire Play now. **Wiring it is safe even with no Play account** - the steps below are gated on a secret that does not exist yet, so they no-op until the dev sets it. Prefer wiring it dormant over leaving it undone.

Keep the APK -> GitHub Release job. Play gets an **AAB**; sideloading still wants the APK. Both come from the same keystore and the same run number.

### What the dev must do by hand (Claude cannot)

Report these as a checklist; do not pretend they are optional.

1. **Pay the $25** one-time Google Play registration (not annual; the $99/yr one is Apple).
2. **Create the app** in Play Console with the exact `applicationId` from `build.gradle.kts`. The package name is permanent once uploaded.
3. **Upload the first AAB manually** through the console. The Google Play Developer API refuses to publish to an app that has never received a manual upload, so CI cannot bootstrap a brand-new listing. Build it locally with `fvm flutter build appbundle --release`.
4. **Service account:** Google Cloud Console (the project linked to Play) -> enable **Google Play Android Developer API** -> create a service account -> create a JSON key. Then Play Console -> **Users and permissions** -> Invite the service account's email -> grant **Release to testing tracks** (plus app access for this app). Permission propagation can take up to 24h - a fresh SA failing with `The caller does not have permission` is usually just this, not a misconfiguration.
5. **Production access, later:** a personal/individual account created after Nov 2023 must run a **closed test with 12+ testers opted in for 14 continuous days** before it can apply for production. The `internal` track is exempt and works immediately, which is why it is the default here.

### Play App Signing

On by default for new apps: Google holds the real app signing key and your Step 2 keystore becomes the **upload key**. No new keystore is needed, and losing the upload key is recoverable (unlike the pre-2021 model). Nothing in Steps 2-3 changes.

### Secret

```bash
gh secret set PLAY_SERVICE_ACCOUNT_JSON --repo <owner/repo> < play-service-account.json
```

Then delete the downloaded JSON from disk. It is a release-capable credential; it does not belong in the repo, in `~/Downloads`, or in a todo file.

### Workflow steps (append to the same job from Step 4)

```yaml
      # The `secrets` context is NOT available in a step-level `if:`, so the presence
      # check must run inside a step and export an output. Gated on the keystore too:
      # Play rejects a debug-signed bundle outright, so uploading one just burns a run.
      - name: Check for Play Store credentials
        id: play
        env:
          PLAY_SERVICE_ACCOUNT_JSON: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON }}
        run: |
          if [ -z "$PLAY_SERVICE_ACCOUNT_JSON" ]; then
            echo "enabled=false" >> "$GITHUB_OUTPUT"
            echo "::notice::No PLAY_SERVICE_ACCOUNT_JSON secret set; skipping Play Store upload."
          elif [ -z "$RELEASE_STORE_FILE" ]; then
            echo "enabled=false" >> "$GITHUB_OUTPUT"
            echo "::warning::Play credentials present but no release keystore; skipping Play Store upload."
          else
            echo "enabled=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Build release AAB
        if: steps.play.outputs.enabled == 'true'
        env:
          RELEASE_STORE_PASSWORD: ${{ secrets.RELEASE_STORE_PASSWORD }}
          RELEASE_KEY_ALIAS: ${{ secrets.RELEASE_KEY_ALIAS }}
          RELEASE_KEY_PASSWORD: ${{ secrets.RELEASE_KEY_PASSWORD }}
        run: flutter build appbundle --release --build-number=${{ github.run_number }}

      # SHA-pinned, not @v1: this step is handed a key with Play release permissions,
      # so a retagged upstream must not be able to silently change what runs here.
      - name: Upload to Play Store (internal track)
        if: steps.play.outputs.enabled == 'true'
        uses: r0adkll/upload-google-play@e738b9dd8f2476ea806d921b64aacd24f34515a5 # v1.1.5
        with:
          serviceAccountJsonPlainText: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON }}
          packageName: <applicationId>
          releaseFiles: build/app/outputs/bundle/release/app-release.aab
          track: internal
          status: completed
```

Re-verify the pin before reusing this block: `gh api repos/r0adkll/upload-google-play/releases/latest --jq .tag_name`, then resolve the tag with `gh api repos/r0adkll/upload-google-play/git/ref/tags/<tag> --jq .object.sha`. Bump both the SHA and the trailing `# vX.Y.Z` comment together.

### Tracks and gotchas

- `track`: `internal` (up to 100 testers, live in minutes, no review wait), `alpha` (closed - the one that satisfies the 12-tester/14-day rule), `beta` (open), `production`.
- `status`: `completed` publishes to that track; use `draft` while the pipeline is unproven so nothing goes live until promoted by hand.
- **`Changes cannot be sent for review automatically`**: add `changesNotSentForReview: true` to the `with:` block. Common on apps that have never completed a full review.
- **`APK specifies a version code that has already been used`**: the run-number scheme in Step 4 was skipped, or the repo's CI history was reset.
- Deobfuscation: add `mappingFile: build/app/outputs/mapping/release/mapping.txt` once the app enables minification.

## Apple / TestFlight

Out of scope here - $99/yr, needs a Mac or a paid macOS runner. `/ios-run` covers the manual build path.
