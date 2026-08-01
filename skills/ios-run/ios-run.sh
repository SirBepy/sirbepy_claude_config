#!/usr/bin/env bash
# ios-run.sh - build the CURRENT Flutter project on the Mac and run it on a connected iPhone, or make a .ipa.
# Driven from the Windows PC over SSH (git-bash provides ssh + tar). See SKILL.md.
# Deploys via Flutter (handles iOS 16 + 17+); devicectl is iOS-17-only so it is NOT used.
set -uo pipefail

# ---------- CONFIG (edit to point at a different Mac) ----------
# SSH hosts tried in order. Tailscale IP first (most reliable from any network), then tailnet name, then LAN.
HOSTS=("100.100.146.54" "josips-macbook-air.tailf0c183.ts.net" "192.168.178.50")
SSH_USER="josipmuzic"
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new"
# Flutter + Homebrew (pod) live outside the non-interactive SSH PATH, so set it explicitly on the Mac.
# This string is duplicated in the remote heredoc below (a quoted heredoc cannot read outer vars).
# ---------------------------------------------------------------

die() { echo "FAIL: $*" >&2; exit 1; }
log() { echo "-> $*" >&2; }

# ---------- arg parse ----------
MODE="run"; LOGS=0; UPLOAD=0; DEVICE_NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    run|ipa)  MODE="$1" ;;
    --logs)   LOGS=1 ;;
    --upload) UPLOAD=1 ;;
    --device) shift; DEVICE_NAME="${1:-}"; [ -n "$DEVICE_NAME" ] || die "--device needs a name" ;;
    *) die "unknown arg: $1 (usage: ios-run.sh [run|ipa] [--logs] [--upload] [--device <name>])" ;;
  esac
  shift
done

# ---------- local: must be a Flutter project ----------
[ -f pubspec.yaml ] || die "not a Flutter project (no pubspec.yaml in $(pwd))"
PROJ="$(basename "$(pwd)")"

# ---------- resolve host ----------
resolve_host() {
  local h err
  for h in "${HOSTS[@]}"; do
    if err="$(ssh $SSH_OPTS "$SSH_USER@$h" true 2>&1)"; then echo "$h"; return 0; fi
    case "$err" in
      *"Permission denied"*|*"publickey"*)
        die "SSH key auth not working for $SSH_USER@$h. Run once:  ssh-copy-id $SSH_USER@$h" ;;
    esac
  done
  return 1
}
HOST="$(resolve_host)" || die "Mac unreachable on any host (${HOSTS[*]}). Wake the Mac / check Tailscale, then re-run."
log "connected: $SSH_USER@$HOST"
SSH=(ssh $SSH_OPTS "$SSH_USER@$HOST")

# ---------- sync working tree (tar over ssh; native Windows, NOT rsync/WSL) ----------
log "syncing $PROJ to Mac ~/projects/$PROJ ..."
tar czf - \
  --exclude=./build --exclude=./.dart_tool --exclude=./.git \
  --exclude=./ios/Pods --exclude=./ios/.symlinks \
  --exclude=./ios/Flutter/Flutter.framework --exclude=./ios/Flutter/ephemeral \
  --exclude=./android/.gradle --exclude=./.idea --exclude='*.iml' \
  . | "${SSH[@]}" "mkdir -p \"\$HOME/projects/$PROJ\" && tar xzf - -C \"\$HOME/projects/$PROJ\""
SYNC_PS=("${PIPESTATUS[@]}")
[ "${SYNC_PS[0]}" -eq 0 ] && [ "${SYNC_PS[1]}" -eq 0 ] || die "tar-over-ssh sync failed"

# ---------- remote: assert, lock, select device (Flutter), build, deploy ----------
"${SSH[@]}" "MODE='$MODE' LOGS='$LOGS' UPLOAD='$UPLOAD' DEVICE_NAME='$DEVICE_NAME' PROJ='$PROJ' bash -s" <<'REMOTE'
set -uo pipefail
die() { echo "FAIL: $*" >&2; exit 1; }
export PATH="$HOME/development/flutter/bin:$HOME/.pub-cache/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

PROJDIR="$HOME/projects/$PROJ"
cd "$PROJDIR" || die "project dir missing on Mac"
[ -d ios/Runner.xcodeproj ] || die "ios/Runner.xcodeproj missing on Mac after sync"
if grep -q envied pubspec.yaml; then
  [ -f .env ] || die ".env missing on Mac after sync (envied codegen will fail)"
fi
command -v flutter >/dev/null 2>&1 || die "flutter not found on Mac (looked in ~/development/flutter/bin)"

# overlap lock
LOCK="$PROJDIR/.ios-run.lock"
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  die "another /ios-run in progress (lock: $LOCK)"
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

caf() { caffeinate -dimsu "$@"; }   # child-scoped: no orphan caffeinate

# ---- device selection (Flutter; works for iOS 16 + 17+) ----
if [ "$MODE" = "run" ]; then
  flutter devices --machine > /tmp/ios-run-fdev.json 2>/dev/null || die "flutter devices failed"
  SEL="$(python3 - "$DEVICE_NAME" <<'PY'
import json, sys
want = sys.argv[1] if len(sys.argv) > 1 else ""
devs = [d for d in json.load(open("/tmp/ios-run-fdev.json"))
        if d.get("targetPlatform") == "ios" and not d.get("emulator", False)]
if want:
    devs = [d for d in devs if d.get("name") == want or d.get("id") == want] or devs
print(len(devs))
for d in devs:
    print(d["id"] + "\t" + d.get("name", "?"))
PY
)"
  N="$(printf '%s\n' "$SEL" | head -1)"
  [ "$N" = "0" ] && die "No iPhone detected by Flutter. Plug it into the Mac via USB, unlock it, and trust the computer."
  if [ "$N" != "1" ]; then
    echo "Multiple iOS devices connected - re-run with --device <name>:" >&2
    printf '%s\n' "$SEL" | tail -n +2 | cut -f2 >&2
    die "Multiple iOS devices connected"
  fi
  DID="$(printf '%s\n' "$SEL" | sed -n '2p' | cut -f1)"
  DNAME="$(printf '%s\n' "$SEL" | sed -n '2p' | cut -f2)"
fi

# ---- build deps ----
caf flutter pub get || die "flutter pub get failed"
if grep -q 'build_runner' pubspec.yaml; then
  # `clean` before `build` is load-bearing: envied reads .env directly via dart:io, and
  # build_runner does NOT treat .env as a tracked input. So a plain `build` keeps a stale
  # env.g.dart whenever only .env changed - including the (gitignored) env.g.dart that the
  # PC->Mac tar-sync just copied over. clean busts the cache so codegen re-reads the synced .env.
  # Past incident (2026-06-11): a rotated voiceover API key 401'd in TestFlight because the synced
  # env.g.dart still baked the old key; `build` alone never refreshed it. clean fixed it.
  caf dart run build_runner clean || die "build_runner clean failed"
  caf dart run build_runner build --delete-conflicting-outputs || die "build_runner codegen failed"
fi

# ---- unlock login keychain in THIS ssh session (codesign needs it; SSH is a separate security session) ----
KCPW="$HOME/.config/ios-run/keychain-pw"
if [ -f "$KCPW" ]; then
  security unlock-keychain -p "$(cat "$KCPW")" "$HOME/Library/Keychains/login.keychain-db" 2>/dev/null \
    || die "keychain unlock failed - wrong password in $KCPW?"
else
  die "login keychain is locked over SSH and no password file found. On the Mac, run once: mkdir -p ~/.config/ios-run && printf '%s' '<your-mac-login-password>' > ~/.config/ios-run/keychain-pw && chmod 600 ~/.config/ios-run/keychain-pw"
fi

# ---- act ----
case "$MODE" in
  ipa)
    caf flutter build ipa || die "flutter build ipa failed (signing? register the iPhone UDID at developer.apple.com or let Xcode auto-manage signing for the Runner target)"
    IPA="$(ls -t build/ios/ipa/*.ipa 2>/dev/null | head -1)"
    [ -n "$IPA" ] || die "no .ipa produced under build/ios/ipa/"
    ABS="$PROJDIR/$IPA"
    if [ "$UPLOAD" = "1" ]; then
      [ -n "${APPLE_ID:-}" ] && [ -n "${APP_SPECIFIC_PASSWORD:-}" ] || die "set APPLE_ID and APP_SPECIFIC_PASSWORD on the Mac to --upload (or drop the flag and use Transporter)"
      xcrun altool --upload-app -f "$ABS" -t ios -u "$APPLE_ID" -p "$APP_SPECIFIC_PASSWORD" || die "altool upload failed"
      echo "OK .ipa uploaded to TestFlight (processing): $ABS"
    else
      echo "OK .ipa ready for Transporter: $ABS"
      echo "   to upload: xcrun altool --upload-app -f \"$ABS\" -t ios -u <apple-id> -p <app-specific-password>"
    fi
    ;;
  run)
    if [ "$LOGS" = "1" ]; then
      echo "OK building + launching with logs on $DNAME (Ctrl-C to stop; the AOT app persists on the phone):"
      caf flutter run --profile -d "$DID"
    else
      caf flutter build ios --profile || die "flutter build ios --profile failed (signing? register the iPhone UDID at developer.apple.com or let Xcode auto-manage signing for the Runner target)"
      caf flutter install --profile -d "$DID" || die "flutter install failed"
      echo "OK $PROJ installed on $DNAME ($DID) - tap the app on your phone to open it"
    fi
    ;;
esac
REMOTE
RC=$?
[ "$RC" -eq 0 ] || exit "$RC"
