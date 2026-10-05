#!/usr/bin/env bash
# Fixture suite for split-hunks.py (todos 1046, 1068). Invoke directly:
#   bash skills/commit/test_split_hunks.sh
# Discovered by ci/run_all.py's skills/commit/test_*.sh glob (once tracked).
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
sh_py="$script_dir/split-hunks.py"

# `python3`/`python` can both resolve to the Windows Store's execution-alias
# stub (prints "Python was not found..." and exits 49) even when a real
# interpreter is installed elsewhere on PATH, so a bare `command -v` is not
# enough - probe that the candidate actually runs before trusting it.
py=""
for candidate in python3 python; do
  if "$candidate" -c "pass" >/dev/null 2>&1; then
    py="$candidate"
    break
  fi
done
if [ -z "$py" ]; then
  echo "FAIL: no working python interpreter found on PATH"
  exit 1
fi

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

new_repo() {
  local d
  d=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
  git -C "$d" init -q
  git -C "$d" config user.email "test@example.com"
  git -C "$d" config user.name "test"
  # Deterministic hunks: autocrlf would turn every line into a line-ending change too, widening
  # every diff hunk to the whole file and breaking the exact assertions below.
  git -C "$d" config core.autocrlf false
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

# --- stage: filters an unstaged file's hunks by substring into the real index ---
d=$(new_repo); tmp_dirs+=("$d")
{
  i=1
  while [ "$i" -le 20 ]; do printf 'line%02d\n' "$i"; i=$((i + 1)); done
} > "$d/file.txt"
git -C "$d" add file.txt
git -C "$d" commit -q -m seed

sed -i '2s/.*/line02-KEEP/' "$d/file.txt"
sed -i '18s/.*/line18-DROP/' "$d/file.txt"

out=$("$py" "$sh_py" --repo "$d" stage file.txt --match KEEP 2>&1); ec=$?
check "stage: exit 0" 0 "" "" "$out" "$ec"
staged=$(git -C "$d" diff --cached -- file.txt)
check "stage: KEEP hunk is staged" 0 "KEEP" "" "$staged" 0
check "stage: DROP hunk is NOT staged" 0 "" "DROP" "$staged" 0
unstaged=$(git -C "$d" diff -- file.txt)
check "stage: DROP hunk stays in the working tree, unstaged" 0 "DROP" "" "$unstaged" 0

# --- stage: no match means nothing staged, exit 1 ---
d2=$(new_repo); tmp_dirs+=("$d2")
printf 'seed\n' > "$d2/no.txt"
git -C "$d2" add no.txt
git -C "$d2" commit -q -m seed
printf 'changed\n' >> "$d2/no.txt"
out=$("$py" "$sh_py" --repo "$d2" stage no.txt --match NOPE 2>&1); ec=$?
check "stage: no match leaves index untouched, exit 1" 1 "nothing staged" "" "$out" "$ec"
check "stage: no match - git diff --cached is empty" 0 "" "." "$(git -C "$d2" diff --cached)" 0

# --- commit: private index + CAS, shared-index peer file survives, resync is scoped ---
d3=$(new_repo); tmp_dirs+=("$d3")
printf 'base\n' > "$d3/own.txt"
{
  i=1
  while [ "$i" -le 20 ]; do printf 'line%02d\n' "$i"; i=$((i + 1)); done
} > "$d3/shared.txt"
printf 'base\n' > "$d3/other.txt"
git -C "$d3" add own.txt shared.txt other.txt
git -C "$d3" commit -q -m seed

# Simulate a THIRD session's already-staged file sitting in the shared index.
printf 'peer-staged\n' > "$d3/other.txt"
git -C "$d3" add other.txt

# Simulate a stale earlier stage of own.txt (what a resync must correct).
printf 'stale-stage\n' > "$d3/own.txt"
git -C "$d3" add own.txt

# Our actual intended whole-file change.
printf 'own-change\n' > "$d3/own.txt"

# shared.txt: our hunk (OURS) plus a peer's own uncommitted hunk (PEER), far enough apart
# to land in two separate @@ blocks.
sed -i '2s/.*/line02-OURS/' "$d3/shared.txt"
sed -i '18s/.*/line18-PEER/' "$d3/shared.txt"

before_head=$(git -C "$d3" rev-parse HEAD)
out=$("$py" "$sh_py" --repo "$d3" commit -m "own + our half of shared" --whole own.txt --hunk shared.txt:OURS 2>&1); ec=$?
check "commit: exit 0" 0 "" "" "$out" "$ec"
after_head=$(git -C "$d3" rev-parse HEAD)
[ "$after_head" != "$before_head" ] && echo "PASS: commit: HEAD advanced" || { echo "FAIL: commit: HEAD did not advance"; fail=1; }

stat=$(git -C "$d3" show --stat HEAD)
check "commit: touches own.txt" 0 "own\.txt" "" "$stat" 0
check "commit: touches shared.txt" 0 "shared\.txt" "" "$stat" 0
check "commit: does NOT touch other.txt" 0 "" "other\.txt" "$stat" 0

worktree_shared=$(git -C "$d3" diff HEAD -- shared.txt)
check "commit: PEER hunk still unstaged in the working tree" 0 "PEER" "" "$worktree_shared" 0
check "commit: OURS hunk is gone from the unstaged diff (already committed)" 0 "" "OURS" "$worktree_shared" 0

cached_names=$(git -C "$d3" diff --cached --name-only)
check "commit: resync cleared own.txt/shared.txt from the real index" 0 "" "^own\.txt$|^shared\.txt$" "$cached_names" 0
check "commit: the peer's staged other.txt survived untouched" 0 "^other\.txt$" "" "$cached_names" 0
other_staged_content=$(git -C "$d3" show :other.txt)
check "commit: other.txt's staged content is still the peer's" 0 "peer-staged" "" "$other_staged_content" 0

# --- commit: CAS refuses when HEAD moved since --base was read ---
d4=$(new_repo); tmp_dirs+=("$d4")
printf 'base\n' > "$d4/f.txt"
git -C "$d4" add f.txt
git -C "$d4" commit -q -m seed
stale_base=$(git -C "$d4" rev-parse HEAD)
# The peer's commit "lands between steps 1 and 3": it happens AFTER stale_base was captured,
# simulating the exact race todo 1068 recorded.
git -C "$d4" commit -q --allow-empty -m "peer commit"
peer_head=$(git -C "$d4" rev-parse HEAD)
printf 'ours\n' >> "$d4/f.txt"

out=$("$py" "$sh_py" --repo "$d4" commit -m "would-be stale commit" --whole f.txt --base "$stale_base" 2>&1); ec=$?
check "commit race: refuses" 1 "HEAD moved" "" "$out" "$ec"
now_head=$(git -C "$d4" rev-parse HEAD)
[ "$now_head" = "$peer_head" ] && echo "PASS: commit race: HEAD left at the peer's commit" || { echo "FAIL: commit race: HEAD is $now_head, want $peer_head"; fail=1; }

if [ "$fail" -ne 0 ]; then
  echo "FAIL: one or more split-hunks.py checks failed"
  exit 1
fi
echo "OK: all split-hunks.py checks passed"
