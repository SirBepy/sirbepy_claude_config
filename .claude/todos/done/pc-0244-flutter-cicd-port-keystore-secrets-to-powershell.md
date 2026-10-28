<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=78c19651 -->
# flutter-cicd: port keystore/secret steps 2 and 5 from bash pipe chains to PowerShell

**Type:** skill-improvement

## Goal

`skills/flutter-cicd/SKILL.md` Step 2 (keystore generation) and Step 5 (repo secrets)
are written as bash command blocks using pipe chains (`|`). This environment's global
shell rules default to PowerShell on Windows and explicitly forbid chaining commands with
`&&`/`;`/`|` in the Bash/PowerShell tool usage - port both steps to PowerShell,
preserving the exact same commands/values, replacing each pipe chain with either a
PowerShell-native equivalent or separate sequential tool calls per the no-chaining rule.

## Context

`skills/flutter-cicd/SKILL.md` (as of 2026-08-01):

**Step 2 - Release keystore** (lines 45-59), bash with a pipe chain generating the
password:
```bash
KS_DIR="$HOME/.android-keystores"; mkdir -p "$KS_DIR"
KS="$KS_DIR/<app>-release.jks"
PASS=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 28)
echo "$PASS" > "$KS_DIR/<app>-release.pass.txt"
keytool -genkeypair -v -keystore "$KS" -storetype JKS -keyalg RSA -keysize 2048 \
  -validity 10000 -alias <app> -storepass "$PASS" -keypass "$PASS" \
  -dname "CN=<App>, OU=SirBepy, O=SirBepy, L=Zagreb, S=Zagreb, C=HR"
```
The `head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 28` chain generates a
28-character random alphanumeric password by taking 24 random bytes, base64-encoding
them, stripping `/`, `+`, `=` characters, then truncating to 28 chars.

**Step 5 - Set repo secrets** (lines 185-196), bash with `|` piping literal secret
values into `gh secret set`:
```bash
REPO=<owner/repo>
base64 -w0 "$KS" | gh secret set RELEASE_KEYSTORE_BASE64 --repo "$REPO"
printf '%s' "$PASS"  | gh secret set RELEASE_STORE_PASSWORD --repo "$REPO"
printf '%s' "<app>"  | gh secret set RELEASE_KEY_ALIAS      --repo "$REPO"
printf '%s' "$PASS"  | gh secret set RELEASE_KEY_PASSWORD   --repo "$REPO"
gh secret list --repo "$REPO"
```

## Approach

1. Read `skills/flutter-cicd/SKILL.md` Step 2 and Step 5 in full before editing (also
   skim Step 4 around lines 183, since versionCode logic references these values too, to
   confirm nothing else depends on the bash-specific variable names being reused
   verbatim).
2. **Step 2 port.** Replace with PowerShell:
   ```powershell
   $KsDir = "$env:USERPROFILE\.android-keystores"
   New-Item -ItemType Directory -Force -Path $KsDir | Out-Null
   ```
   ```powershell
   $Bytes = New-Object byte[] 24
   [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
   $Pass = ([Convert]::ToBase64String($Bytes) -replace '[/+=]', '').Substring(0, 28)
   Set-Content -Path "$KsDir\<app>-release.pass.txt" -Value $Pass -NoNewline -Encoding utf8
   ```
   (matches the original's entropy source and character-stripping/truncation exactly -
   24 random bytes, strip `/+=`, take first 28 chars). Keep `keytool` invocation as a
   separate PowerShell call (it's a real cross-platform Java tool, not a bash-ism, so its
   own command line does not need translation, only quoting/line-continuation syntax
   adjusted for PowerShell using backtick line continuation or a single-line call).
3. **Step 5 port.** Replace stdin-piped `gh secret set` calls with PowerShell's
   `--body`-file or stdin-via-variable pattern. `gh secret set` supports reading from a
   file via `--body <file>` or from a literal value; check current `gh` CLI syntax for the
   cleanest non-piped form, e.g.:
   ```powershell
   $KsB64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($Ks))
   gh secret set RELEASE_KEYSTORE_BASE64 --repo $Repo --body $KsB64
   ```
   repeated per secret (`RELEASE_STORE_PASSWORD`, `RELEASE_KEY_ALIAS`,
   `RELEASE_KEY_PASSWORD`), each as its OWN separate command per the global no-chaining
   rule (never combine into one call with `;`). Confirm `gh secret set --body` accepts a
   literal string argument directly (vs requiring a file path) against the currently
   installed `gh` version before finalizing - fall back to writing to a temp file and
   passing `--body-file <path>` (then deleting the temp file) if `--body` requires a
   file.
4. Verify the base64 encoding of the keystore file itself matches what `base64 -w0`
   produced (no line wrapping) - `[Convert]::ToBase64String` produces unwrapped base64 by
   default, matching `-w0`'s intent, but confirm empirically against a real keystore file
   before trusting it blindly.
5. Update any prose in the file that assumes bash syntax (e.g. `$HOME` references
   elsewhere in Step 2's surrounding text) to PowerShell equivalents (`$env:USERPROFILE`).

## Acceptance

- Steps 2 and 5 contain PowerShell commands only, no `|` pipe chains, no bash-specific
  syntax (`$HOME`, `head -c`, `tr -d`).
- Each command is written as a separate, independently-runnable PowerShell call (no `;`
  or `&&` chaining), matching the global shell rule.
- Run the ported Step 2 against a real (throwaway/test) app name to confirm it produces a
  valid keystore and a 28-character password matching the original algorithm's output
  shape, then run the ported Step 5 against a scratch/test repo to confirm the secrets
  land correctly (`gh secret list --repo <test-repo>` shows all four names).

## Notes

- completed, commit 937f802
