#!/usr/bin/env bash
# Fixture suite for watch-build.ps1. Invoke directly:
#   bash skills/commit/test_watch_build.sh
# Discovered by ci/run_all.py's skills/commit/test_*.sh glob.
#
# watch-build.ps1 only talks to GitHub through `gh`, so the suite puts a fake gh.cmd first on PATH
# that answers from JSON fixtures. The script is copied beside the fake so its PID file lands in
# the scratch dir instead of clobbering a live watcher's.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd -P)

if ! command -v pwsh >/dev/null 2>&1; then
  echo "SKIP: pwsh not on PATH, watch-build.ps1 cannot run"
  exit 0
fi

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

root=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$root")
cp "$script_dir/watch-build.ps1" "$root/watch-build.ps1"

cat > "$root/gh.cmd" <<'EOF'
@pwsh -NoProfile -File "%~dp0gh-fake.ps1" %*
EOF

cat > "$root/gh-fake.ps1" <<'EOF'
$a = $args -join ' '
$dir = $env:GH_FAKE_DIR
if ($a -match '^repo view') { 'o/r'; exit 0 }
if ($a -match '^run list') { Get-Content "$dir/runs.json" -Raw; exit 0 }
if ($a -match '^run watch') { exit 0 }
if ($a -match '^run view (\d+) .*--log-failed') { "failed-step log for $($Matches[1])"; exit 0 }
if ($a -match '^run view (\d+) .*--json jobs') { Get-Content "$dir/jobs-$($Matches[1]).json" -Raw; exit 0 }
if ($a -match '^run view (\d+) .*--json status,conclusion') { Get-Content "$dir/view-$($Matches[1]).json" -Raw; exit 0 }
exit 1
EOF

sha=0123456789abcdef0123456789abcdef01234567

check() {
  local desc=$1 want_exit=$2 want_pattern=$3 unwant_pattern=$4 out=$5 got_exit=$6
  if [ "$got_exit" != "$want_exit" ]; then
    echo "FAIL: $desc - exit $got_exit, want $want_exit (out: $out)"
    fail=1
    return
  fi
  if [ -n "$want_pattern" ] && ! printf '%s' "$out" | grep -qE "$want_pattern"; then
    echo "FAIL: $desc - output missing /$want_pattern/: $out"
    fail=1
    return
  fi
  if [ -n "$unwant_pattern" ] && printf '%s' "$out" | grep -qE "$unwant_pattern"; then
    echo "FAIL: $desc - output unexpectedly matched /$unwant_pattern/: $out"
    fail=1
    return
  fi
  echo "PASS: $desc"
}

# fixture <name> <runs-json-array>: a fresh fixture dir; per-run files are added by the caller.
new_fixture() {
  local d
  d=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
  tmp_dirs+=("$d")
  printf '%s' "$1" > "$d/runs.json"
  printf '%s' "$d"
}

# run_watcher <fixture-dir> [extra watch-build args...]
run_watcher() {
  local fx=$1; shift
  GH_FAKE_DIR=$(cygpath -m "$fx") PATH="$(cygpath -u "$root"):$PATH" \
    pwsh -NoProfile -File "$(cygpath -w "$root")\\watch-build.ps1" -Branch main -Sha "$sha" \
    -RepoPath "$(cygpath -w "$root")" -GraceSeconds 0 "$@" 2>&1
}

run_entry() { printf '{"databaseId":%s,"headSha":"%s","status":"completed","workflowName":"%s"}' "$1" "$sha" "$2"; }

# All green: the marker stays success.
fx=$(new_fixture "[$(run_entry 101 CI)]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-101.json"
printf '{"jobs":[{"name":"test","conclusion":"success"}]}' > "$fx/jobs-101.json"
out=$(run_watcher "$fx"); rc=$?
check "an all-green run reports success" 0 'BUILD_RESULT=success' 'cancelled' "$out" "$rc"

# The 2026-11-06 shape: the macOS job was cancelled, tag and publish were skipped, nothing shipped.
fx=$(new_fixture "[$(run_entry 102 'Tauri Release')]")
printf '{"status":"completed","conclusion":"cancelled"}' > "$fx/view-102.json"
printf '{"jobs":[{"name":"build (macos)","conclusion":"cancelled"},{"name":"tag","conclusion":"skipped"},{"name":"publish","conclusion":"skipped"}]}' > "$fx/jobs-102.json"
out=$(run_watcher "$fx"); rc=$?
check "a cancelled workflow is reported as cancelled, never success, naming the job" \
  5 'BUILD_RESULT=cancelled.*Tauri Release run 102.*build \(macos\)' 'BUILD_RESULT=success' "$out" "$rc"

# A cancelled job inside a run whose workflow still concluded success is just as unpublished.
fx=$(new_fixture "[$(run_entry 103 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-103.json"
printf '{"jobs":[{"name":"build (linux)","conclusion":"success"},{"name":"build (macos)","conclusion":"cancelled"}]}' > "$fx/jobs-103.json"
out=$(run_watcher "$fx"); rc=$?
check "a cancelled job under a success conclusion is still reported as cancelled" \
  5 'BUILD_RESULT=cancelled.*build \(macos\)' 'BUILD_RESULT=success' "$out" "$rc"

# A skipped publish job after a push that was meant to release.
fx=$(new_fixture "[$(run_entry 104 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-104.json"
printf '{"jobs":[{"name":"build","conclusion":"success"},{"name":"publish","conclusion":"skipped"}]}' > "$fx/jobs-104.json"
out=$(run_watcher "$fx" -ExpectPublish); rc=$?
check "-ExpectPublish turns a skipped publish job into publish_skipped" \
  6 'BUILD_RESULT=publish_skipped.*publish' 'BUILD_RESULT=success' "$out" "$rc"
out=$(run_watcher "$fx"); rc=$?
check "without -ExpectPublish the same skipped publish job stays success (a plain push publishes nothing)" \
  0 'BUILD_RESULT=success' 'publish_skipped' "$out" "$rc"

# Under -ExpectPublish an unreadable job list is not "nothing was skipped": no jobs fixture here,
# so the fake gh prints nothing for `--json jobs`.
fx=$(new_fixture "[$(run_entry 107 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-107.json"
out=$(run_watcher "$fx" -ExpectPublish); rc=$?
check "-ExpectPublish with an unreadable job list reports watch_error, never success" \
  3 'BUILD_RESULT=watch_error' 'BUILD_RESULT=success' "$out" "$rc"

# A job list of `{"jobs":null}` is unreadable too, and a hyphenated publish job still counts.
fx=$(new_fixture "[$(run_entry 109 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-109.json"
printf '{"jobs":null}' > "$fx/jobs-109.json"
out=$(run_watcher "$fx" -ExpectPublish); rc=$?
check "-ExpectPublish with a null job list reports watch_error" 3 'BUILD_RESULT=watch_error' 'BUILD_RESULT=success' "$out" "$rc"
fx=$(new_fixture "[$(run_entry 110 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-110.json"
printf '{"jobs":[{"name":"build","conclusion":"success"},{"name":"publish-tauri","conclusion":"skipped"}]}' > "$fx/jobs-110.json"
out=$(run_watcher "$fx" -ExpectPublish); rc=$?
check "-ExpectPublish catches a skipped hyphenated publish job" 6 'BUILD_RESULT=publish_skipped.*publish-tauri' 'BUILD_RESULT=success' "$out" "$rc"

# Only a publish/release job counts; release-notes or build-release skipping is routine.
fx=$(new_fixture "[$(run_entry 108 'Tauri Release')]")
printf '{"status":"completed","conclusion":"success"}' > "$fx/view-108.json"
printf '{"jobs":[{"name":"build","conclusion":"success"},{"name":"release-notes","conclusion":"skipped"},{"name":"build-release","conclusion":"skipped"}]}' > "$fx/jobs-108.json"
out=$(run_watcher "$fx" -ExpectPublish); rc=$?
check "-ExpectPublish ignores skipped jobs that only contain the word release" \
  0 'BUILD_RESULT=success' 'publish_skipped' "$out" "$rc"

# A real failure outranks a cancellation in a sibling run.
fx=$(new_fixture "[$(run_entry 105 CI),$(run_entry 106 'Tauri Release')]")
printf '{"status":"completed","conclusion":"failure"}' > "$fx/view-105.json"
printf '{"jobs":[{"name":"test","conclusion":"failure"}]}' > "$fx/jobs-105.json"
printf '{"status":"completed","conclusion":"cancelled"}' > "$fx/view-106.json"
printf '{"jobs":[{"name":"build (macos)","conclusion":"cancelled"}]}' > "$fx/jobs-106.json"
out=$(run_watcher "$fx"); rc=$?
check "a failed run still reports failure when a sibling run was cancelled" \
  1 'BUILD_RESULT=failure' 'BUILD_RESULT=cancelled' "$out" "$rc"

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
