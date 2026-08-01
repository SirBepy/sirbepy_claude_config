---
name: ios-run
description: Builds the current Flutter project on the dev's Mac over SSH and runs it on a connected iPhone, or builds a TestFlight .ipa.
disable-model-invocation: true
argument-hint: "[run|ipa] [--logs] [--upload] [--device <name>]"
---

# /ios-run

> Build the current Flutter project on the Mac over SSH and run it on a connected iPhone (or make a TestFlight .ipa).

Drives the dev's Mac as a headless iOS build box from the Windows PC. The PC has no rsync and cannot deploy to an iPhone directly, so all building/installing happens on the Mac (iPhone plugged into the Mac via USB) and is triggered over SSH. Deploys via Flutter, which handles iOS 16 and 17+ (Apple's `devicectl` is iOS-17-only, so it is NOT used). Stateless, idempotent, fail-loud. Flutter projects only.

## When to use

The dev runs `/ios-run` from inside a Flutter project directory on the PC to see that project running on the physical iPhone, or to produce an uploadable `.ipa`. Never auto-fires.

## Modes

| Invocation | What it does |
|---|---|
| `/ios-run` or `/ios-run run` | sync, build profile, install on the iPhone; tap the app to open it |
| `/ios-run run --logs` | sync, build profile, `flutter run --profile` in the foreground (launches + streams logs, Ctrl-C to stop; the AOT app persists) |
| `/ios-run ipa` | sync, `flutter build ipa`, print the `.ipa` path for Transporter |
| `/ios-run ipa --upload` | same, then upload via `xcrun altool` (needs `APPLE_ID` + `APP_SPECIFIC_PASSWORD` set on the Mac) |
| `... --device <name>` | required only when more than one iPhone is connected |

## How to run it

From the project root, via the Bash tool (git-bash provides `ssh` + `tar`):

```
bash ~/.claude/skills/ios-run/ios-run.sh <run|ipa> [--logs] [--upload] [--device <name>]
```

Builds are slow (the first `pod install` + xcodebuild can take a few minutes), so run it with `run_in_background: true` and read the output file when it completes. Then relay the result: `OK ...` on success, or a plain-English `FAIL: ...` line with the remediation.

## One-time setup (per machine, all verified working)

The skill assumes these are done. Each maps to a `FAIL:` message that names the fix if missing:

1. **SSH key, PC -> Mac.** Generate on the PC (`ssh-keygen -t ed25519`), install on the Mac (`ssh-copy-id josipmuzic@<host>`). Without it every call would hang on a password prompt; `BatchMode=yes` turns that into a clean failure with the remediation.
2. **Keychain code-signing access.** Once on the Mac: `security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k <login-pw> ~/Library/Keychains/login.keychain-db`. Lets codesign tools use the signing key without a GUI prompt.
3. **Keychain unlock password file.** On the Mac: write the login password to `~/.config/ios-run/keychain-pw` (chmod 600). An SSH session is a separate security session where the login keychain is locked; the skill unlocks it in-session from this file before building. Tradeoff: the login password sits in a 600 file (acceptable for a personal box; a dedicated signing keychain is the more-secure alternative).
4. **Reachability.** Mac awake + on the network. Tailscale on the PC makes it work off-LAN; otherwise same-WiFi only.

## Connection (config at the top of the script)

Tries, in order: Tailscale IP, Tailscale hostname, then LAN IP, as user `josipmuzic`. Every SSH call uses `-o BatchMode=yes -o ConnectTimeout=8`. To change machines, edit the `HOSTS` / `SSH_USER` vars at the top of `ios-run.sh`.

## Guarantees baked into the script

- **No native rsync / no WSL:** sync is `tar`-over-SSH from native Windows (WSL2 does not share the Windows SSH keys or the Tailscale route).
- **Mandatory paths sync:** the `ios/` tree (Xcode project, Podfile, signing) and the gitignored `.env` always sync (only `ios/Pods`, build artifacts, and VCS/IDE junk are excluded), with a post-sync assertion.
- **Explicit Mac PATH:** non-interactive SSH gets a minimal PATH, so the script sets flutter (`~/development/flutter/bin`) and Homebrew (`/opt/homebrew/bin`, for `pod`) explicitly rather than relying on the login shell.
- **No orphans:** `caffeinate -dimsu` is child-scoped to each remote command; a PID lock file with a `trap` cleanup prevents overlapping runs.

## Not in scope (v1)

Debug-mode hot reload, native/React-Native projects, wake-on-LAN, auto-launch in default `run` (use `--logs` to launch, or tap the app). Hot reload is a planned v2 (needs a persistent remote `flutter run` session plus a file-watcher).
