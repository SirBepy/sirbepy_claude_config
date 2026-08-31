# Play Store upload (Step 7 bolt-on)

Read this only after the dev has confirmed (per SKILL.md's `[TOOLING]`
ask-gate) that Play should be wired.

Keep the APK -> GitHub Release job. Play gets an **AAB**; sideloading still wants the APK. Both come from the same keystore and the same run number.

## What the dev must do by hand (Claude cannot)

Report these as a checklist; do not pretend they are optional.

1. **Organisation account: verify the org's website first.** Signup blocks on it. Verify the site in Google **Search Console as a URL-prefix property** - a Domain property needs DNS control, so it is impossible on `github.io`. A `sites.google.com/view/` page is a dead end: Search Console's HTML token cannot be uploaded to it. If the site is an SSG build (Vite, Astro, Next), the token file goes in the source `public/` dir, NOT the repo root, or it 404s after deploy.
2. **Pay the $25** one-time Google Play registration (not annual; the $99/yr one is Apple). Payment gotcha: for an org account Google prefills the cardholder name with the **organisation** name, so a card embossed with a person's name gets rejected by the issuer and Google reports `OR_MIVEM_04` "your card couldn't be verified" - which reads like a bank fault and sends you chasing the wrong thing. Overwrite the prefilled name and billing address to match the card. A personal card is acceptable for an org account.
3. **Create the app** in Play Console with the exact `applicationId` from `build.gradle.kts`. The package name is permanent once uploaded.
4. **Upload the first AAB manually** through the console. The Google Play Developer API refuses to publish to an app that has never received a manual upload, so CI cannot bootstrap a brand-new listing. Build it locally with `fvm flutter build appbundle --release`.
5. **Service account:** Google Cloud Console (the project linked to Play) -> enable **Google Play Android Developer API** -> create a service account -> create a JSON key. Then Play Console -> **Users and permissions** -> Invite the service account's email -> grant **Release to testing tracks** (plus app access for this app). Permission propagation can take up to 24h - a fresh SA failing with `The caller does not have permission` is usually just this, not a misconfiguration.
6. **Production access, later:** a personal/individual account created after Nov 2023 must run a **closed test with 12+ testers opted in for 14 continuous days** before it can apply for production. The `internal` track is exempt and works immediately, which is why it is the default here.

## Play App Signing

On by default for new apps: Google holds the real app signing key and your Step 2 keystore becomes the **upload key**. No new keystore is needed, and losing the upload key is recoverable (unlike the pre-2021 model). Nothing in Steps 2-3 changes.

## Secret

```bash
gh secret set PLAY_SERVICE_ACCOUNT_JSON --repo <owner/repo> < play-service-account.json
```

Then delete the downloaded JSON from disk. It is a release-capable credential; it does not belong in the repo, in `~/Downloads`, or in a todo file.

## Workflow steps (append to the same job from Step 4)

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

## Tracks and gotchas

- `track`: `internal` (up to 100 testers, live in minutes, no review wait), `alpha` (closed - the one that satisfies the 12-tester/14-day rule), `beta` (open), `production`.
- `status`: `completed` publishes to that track; use `draft` while the pipeline is unproven so nothing goes live until promoted by hand.
- **`Changes cannot be sent for review automatically`**: add `changesNotSentForReview: true` to the `with:` block. Common on apps that have never completed a full review.
- **`APK specifies a version code that has already been used`**: the run-number scheme in Step 4 was skipped, or the repo's CI history was reset.
- Deobfuscation: add `mappingFile: build/app/outputs/mapping/release/mapping.txt` once the app enables minification.
