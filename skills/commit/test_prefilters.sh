#!/usr/bin/env bash
# Fixture suite for secret-scan.sh, comment-noise.sh, em-dash.sh, overlap-check.sh (todo 810),
# seeded from done/412, done/460, done/456, done/778. Invoke directly:
#   bash skills/commit/test_prefilters.sh
# Sibling test_comment_noise.sh (todo 903) already covers comment-noise.sh's cut-ratio math.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
gate="$script_dir/prefilter-gate.sh"
secret_scan="$script_dir/secret-scan.sh"
comment_noise="$script_dir/comment-noise.sh"
em_dash="$script_dir/em-dash.sh"
overlap_check="$script_dir/overlap-check.sh"

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

new_repo() {
  local d
  d=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
  # Every caller runs this via `x=$(new_repo)`, a subshell whose own tmp_dirs append never
  # reaches the parent's array - the caller must register $d itself, right after this returns.
  git -C "$d" init -q
  git -C "$d" config user.email "test@example.com"
  git -C "$d" config user.name "test"
  # Deterministic hunks: autocrlf would turn every line into a line-ending change too, widening
  # every diff hunk to the whole file and breaking exact-range assertions below.
  git -C "$d" config core.autocrlf false
  printf 'seed\n' > "$d/README.md"
  git -C "$d" add README.md
  git -C "$d" commit -q -m seed
  printf '%s' "$d"
}

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

# --- secret-scan.sh: blind inside a foreign git root (done/412) ---
# A separate repo nested in the parent's working tree reproduces the gate's per-path
# repo-grouping without needing a real `git submodule add`; the bug was root resolution, not
# the gitlink record.
parent=$(new_repo); tmp_dirs+=("$parent")
mkdir -p "$parent/vendor/sub"
git -C "$parent/vendor/sub" init -q
git -C "$parent/vendor/sub" config user.email "test@example.com"
git -C "$parent/vendor/sub" config user.name "test"
printf 'seed\n' > "$parent/vendor/sub/README.md"
git -C "$parent/vendor/sub" add README.md
git -C "$parent/vendor/sub" commit -q -m seed
# Built from two halves so this script's OWN source line never contains the contiguous
# token shape secret-scan.sh looks for and flags itself.
fake_tok="ghp_""abcdefghij1234567890abcdef"
printf 'const tok = "%s";\n' "$fake_tok" > "$parent/vendor/sub/config.js"
out=$(cd "$parent" && "$gate" vendor/sub/config.js); rc=$?
check "secret-scan.sh sees a planted credential inside a foreign repo root" \
  1 'config\.js:1: ghp_' '' "$out" "$rc"

# --- secret-scan.sh: blind on a gitignored path (done/460) ---
repo=$(new_repo); tmp_dirs+=("$repo")
printf '*\n' > "$repo/.gitignore"
fake_tok2="ghp_""zyxwvutsrqponmlkjihgfed"
printf 'const tok = "%s";\n' "$fake_tok2" > "$repo/secrets.txt"
out=$(cd "$repo" && "$gate" secrets.txt); rc=$?
check "secret-scan.sh sees a planted credential in a gitignored file" \
  1 'secrets\.txt:1: ghp_' '' "$out" "$rc"

printf 'nothing to see here\n' > "$repo/clean.txt"
out=$(cd "$repo" && "$gate" clean.txt); rc=$?
check "an unremarkable gitignored file still clears the gate" 0 '' '' "$out" "$rc"

# --- comment-noise.sh: generated-file skip, filename suffix only (done/456) ---
# comment-noise.sh's own exit code is sort's (always 0), so this checks stdout content only;
# the gate integration is already covered by the secret-scan cases above.
gen=$(new_repo); tmp_dirs+=("$gen")
write_noisy() {
  local path=$1 i
  : > "$path"
  for i in 1 2 3 4 5 6; do printf '// note %d\n' "$i" >> "$path"; done
  for i in $(seq 1 18); do printf 'var x = %d;\n' "$i" >> "$path"; done
}
write_noisy "$gen/model.freezed.dart"
write_noisy "$gen/model.dart"
mkdir -p "$gen/generated"
write_noisy "$gen/generated/model.dart"
out=$(cd "$gen" && bash "$comment_noise" model.freezed.dart model.dart generated/model.dart)
if printf '%s' "$out" | grep -qF 'model.freezed.dart'; then
  echo "FAIL: comment-noise.sh flagged a .freezed.dart file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qE '^model\.dart '; then
  echo "FAIL: comment-noise.sh did not flag the hand-written model.dart: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qE '^generated/model\.dart '; then
  echo "FAIL: comment-noise.sh skipped a hand-written file merely sitting under generated/: $out"
  fail=1
else
  echo "PASS: comment-noise.sh skips by filename suffix, not by directory"
fi

# --- em-dash.sh: exempt marker honored under .claude/todos/ only (done/778) ---
ed=$(new_repo); tmp_dirs+=("$ed")
mkdir -p "$ed/.claude/todos" "$ed/other"
ED=$(printf '\xe2\x80\x94')
printf '<!-- em-dash-exempt -->\nhas a %s dash\n' "$ED" > "$ed/.claude/todos/exempt.md"
printf 'has a %s dash\n' "$ED" > "$ed/.claude/todos/flagged.md"
printf '<!-- em-dash-exempt -->\nhas a %s dash\n' "$ED" > "$ed/other/outside.md"
out=$(cd "$ed" && bash "$em_dash" .claude/todos/exempt.md .claude/todos/flagged.md other/outside.md)
if printf '%s' "$out" | grep -qF 'exempt.md'; then
  echo "FAIL: em-dash.sh flagged a marked todo file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qF 'flagged.md'; then
  echo "FAIL: em-dash.sh did not flag an unmarked todo file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qF 'outside.md'; then
  echo "FAIL: em-dash.sh honored the marker outside .claude/todos/: $out"
  fail=1
else
  echo "PASS: em-dash.sh's marker is scoped to .claude/todos/ exactly"
fi

# --- overlap-check.sh: no upstream is clean, a real hunk overlap is a hit ---
noup=$(new_repo); tmp_dirs+=("$noup")
printf 'seed\nline2\n' > "$noup/file.txt"
git -C "$noup" add file.txt
git -C "$noup" commit -q -m "add file"
printf 'seed\nline2 changed\n' > "$noup/file.txt"
out=$(cd "$noup" && "$overlap_check" file.txt); rc=$?
check "overlap-check.sh is clean with no upstream configured" 0 '' '' "$out" "$rc"

remote=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$remote")
git init -q --bare "$remote"
local=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$local")
git init -q "$local"
git -C "$local" config user.email "test@example.com"
git -C "$local" config user.name "test"
git -C "$local" config core.autocrlf false
git -C "$local" checkout -q -b master
git -C "$local" remote add origin "$remote"
printf 'line1\nline2\nline3\n' > "$local/f.txt"
git -C "$local" add f.txt
git -C "$local" commit -q -m seed
git -C "$local" push -q -u origin master
printf 'line1\nCHANGED2\nline3\n' > "$local/f.txt"
git -C "$local" commit -q -am "change line2"
printf 'line1\nCHANGED2-AGAIN\nline3\n' > "$local/f.txt"
out=$(cd "$local" && "$overlap_check" f.txt); rc=$?
check "overlap-check.sh reports a hunk-level hit against an unpushed local commit" \
  1 'f\.txt:[0-9]+-[0-9]+ [0-9a-f]{7,40} change line2' '' "$out" "$rc"

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
