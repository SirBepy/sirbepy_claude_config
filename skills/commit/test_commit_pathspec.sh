#!/usr/bin/env bash
# Fixture suite for commit-pathspec.sh (todo 964). Invoke directly:
#   bash skills/commit/test_commit_pathspec.sh
# Discovered by ci/run_all.py's skills/commit/test_*.sh glob.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
cp="$script_dir/commit-pathspec.sh"

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
  # Deterministic hunks: autocrlf would turn every line into a line-ending change, widening
  # every hunk to the whole file and breaking the exact-range assertions below.
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

# --- clean commit end-to-end, with a REAL multi-hunk diff and NO --own-range given: proves
# the auto-derive path (todo 924/933) against two separate hunks in one file, not a synthetic
# single-line change ---
r1=$(new_repo); tmp_dirs+=("$r1")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r1/multi.txt"
git -C "$r1" add multi.txt
git -C "$r1" commit -q -m "seed multi.txt"
branch=$(git -C "$r1" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r1" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r1/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r1/multi.txt"
out=$("$cp" -C "$r1" --expect-branch "$branch" --expect-sha "$sha" -m "edit two hunks" -- multi.txt 2>&1); rc=$?
# Ranges are whole-hunk spans (default 3-line diff context on each side of the changed line,
# same convention foreign-hunk-check.sh's own doc comment describes), not single-line: line 3's
# edit widens to 1-6, line 20's to 17-23.
check "clean multi-hunk commit: auto-derived own-range covers both hunks" \
  0 'auto-derived own-range 1-6,17-23' 'REFUSED' "$out" "$rc"
new_head=$(git -C "$r1" rev-parse HEAD)
last_line=$(printf '%s' "$out" | tail -n1)
if [ "$last_line" != "$new_head" ]; then
  echo "FAIL: clean commit - last printed line ($last_line) is not the new HEAD ($new_head)"
  fail=1
else
  echo "PASS: clean commit - last line is the full new HEAD sha"
fi
if [ "$new_head" = "$sha" ]; then
  echo "FAIL: clean commit - HEAD did not move"
  fail=1
else
  echo "PASS: clean commit - HEAD advanced"
fi

# --- pathspec including a deleted path: no manual filtering needed, deletion classified and
# excluded from the diff-based checks while a live file in the same pathspec still gets them ---
r2=$(new_repo); tmp_dirs+=("$r2")
printf 'keep me\nline2\n' > "$r2/keep.txt"
printf 'gone soon\n' > "$r2/gone.txt"
git -C "$r2" add keep.txt gone.txt
git -C "$r2" commit -q -m "seed keep+gone"
branch=$(git -C "$r2" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r2" rev-parse HEAD)
git -C "$r2" rm -q gone.txt
sed -i '2s/.*/line2 EDITED/' "$r2/keep.txt"
out=$("$cp" -C "$r2" --expect-branch "$branch" --expect-sha "$sha" -m "delete gone.txt, edit keep.txt" -- gone.txt keep.txt 2>&1); rc=$?
check "pathspec with a staged-deleted path commits cleanly, no manual filtering" \
  0 'gone\.txt: deleted-staged \(excluded' 'REFUSED|ERROR' "$out" "$rc"
if git -C "$r2" ls-files --error-unmatch -- gone.txt >/dev/null 2>&1; then
  echo "FAIL: gone.txt is still tracked after the commit"
  fail=1
else
  echo "PASS: gone.txt's deletion actually landed"
fi

# --- foreign hunk present must be SURFACED, never swallowed: two separate hunks, only one
# declared via --own-range, the other must block; then --force foreign-hunk lets it through ---
r3=$(new_repo); tmp_dirs+=("$r3")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r3/shared.txt"
git -C "$r3" add shared.txt
git -C "$r3" commit -q -m "seed shared.txt"
branch=$(git -C "$r3" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r3" rev-parse HEAD)
# Line 2: mine. Line 20: an edit I did NOT declare, standing in for a peer's working-tree line
# in a shared checkout - foreign-hunk-check has no other way to know it isn't mine.
sed -i '2s/.*/line 02 MINE/' "$r3/shared.txt"
sed -i '20s/.*/line 20 NOT-MINE/' "$r3/shared.txt"
out=$("$cp" -C "$r3" --expect-branch "$branch" --expect-sha "$sha" --own-range shared.txt:2-2 \
  -m "should be refused" -- shared.txt 2>&1); rc=$?
check "an undeclared second hunk is surfaced, not silently swallowed" \
  1 'foreign-hunk-check.*REFUSED' '' "$out" "$rc"
if [ "$(git -C "$r3" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: a refused foreign-hunk-check must not have committed anything"
  fail=1
else
  echo "PASS: refused foreign-hunk-check left HEAD untouched"
fi
out=$("$cp" -C "$r3" --expect-branch "$branch" --expect-sha "$sha" --own-range shared.txt:2-2 \
  --force foreign-hunk -m "forced through" -- shared.txt 2>&1); rc=$?
check "--force foreign-hunk proceeds past the same surfaced hit" \
  0 'OVERRIDDEN \(--force foreign-hunk\)' 'REFUSED' "$out" "$rc"

# --- branch guard: never overridable ---
r4=$(new_repo); tmp_dirs+=("$r4")
git -C "$r4" checkout -q -b feature-x
printf 'x\n' >> "$r4/README.md"
out=$("$cp" -C "$r4" --expect-branch "master" --expect-sha "$(git -C "$r4" rev-parse HEAD)" \
  -m "wrong branch" -- README.md 2>&1); rc=$?
check "branch guard refuses on a mismatched branch" \
  1 'branch-guard.*REFUSED.*expected master, HEAD is on feature-x' '' "$out" "$rc"
out=$("$cp" -C "$r4" --force branch-guard --expect-branch "master" \
  --expect-sha "$(git -C "$r4" rev-parse HEAD)" -m "x" -- README.md 2>&1); rc=$?
check "branch-guard is never a valid --force target" 2 'never accepted' '' "$out" "$rc"

# --- HEAD guard: a peer commit landing here is a judgement call, refused then --force ---
r5=$(new_repo); tmp_dirs+=("$r5")
stale_sha=$(git -C "$r5" rev-parse HEAD)
branch=$(git -C "$r5" rev-parse --abbrev-ref HEAD)
printf 'peer commit\n' >> "$r5/README.md"
git -C "$r5" commit -q -am "simulated peer commit"
printf 'new file\n' > "$r5/new.txt"
git -C "$r5" add new.txt
out=$("$cp" -C "$r5" --expect-branch "$branch" --expect-sha "$stale_sha" -m "stale head" -- new.txt 2>&1); rc=$?
check "HEAD guard refuses and prints both shas on a moved HEAD" \
  1 "head-guard.*REFUSED: expected $stale_sha, HEAD is now" '' "$out" "$rc"
out=$("$cp" -C "$r5" --expect-branch "$branch" --expect-sha "$stale_sha" --force head-guard \
  -m "proceeding anyway" -- new.txt 2>&1); rc=$?
check "--force head-guard proceeds past a moved HEAD" \
  0 'OVERRIDDEN \(--force head-guard\)' 'REFUSED' "$out" "$rc"

# --- coverage check: a half-committed rename (dest named, source left out in the same dir) ---
r6=$(new_repo); tmp_dirs+=("$r6")
mkdir -p "$r6/src"
printf 'moved content\n' > "$r6/src/old.txt"
git -C "$r6" add src/old.txt
git -C "$r6" commit -q -m "seed src/old.txt"
branch=$(git -C "$r6" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r6" rev-parse HEAD)
git -C "$r6" mv src/old.txt src/new.txt
out=$("$cp" -C "$r6" --expect-branch "$branch" --expect-sha "$sha" -m "only the destination" -- src/new.txt 2>&1); rc=$?
check "coverage check refuses a half-named same-directory move" \
  1 'coverage-check.*REFUSED.*src/old\.txt' '' "$out" "$rc"
out=$("$cp" -C "$r6" --expect-branch "$branch" --expect-sha "$sha" --force coverage \
  -m "deliberately partial" -- src/new.txt 2>&1); rc=$?
check "--force coverage proceeds past the same half-named move" \
  0 'OVERRIDDEN \(--force coverage\)' 'REFUSED' "$out" "$rc"

# --- prefilter gate: a flagged secret blocks and is never overridable via any --force ---
r7=$(new_repo); tmp_dirs+=("$r7")
branch=$(git -C "$r7" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r7" rev-parse HEAD)
fake_tok="ghp_""abcdefghij1234567890abcdef"
printf 'const tok = "%s";\n' "$fake_tok" > "$r7/config.js"
out=$("$cp" -C "$r7" --expect-branch "$branch" --expect-sha "$sha" -m "should never land" -- config.js 2>&1); rc=$?
check "prefilter gate blocks a planted secret, never overridable" \
  1 'prefilter-gate.*FLAGGED.*never overridable' '' "$out" "$rc"
if [ "$(git -C "$r7" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: a secret-flagged commit must not have landed"
  fail=1
else
  echo "PASS: secret-flagged commit did not land"
fi

# --- a brand-new untracked file is staged and committed without a separate `git add` step ---
r8=$(new_repo); tmp_dirs+=("$r8")
branch=$(git -C "$r8" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r8" rev-parse HEAD)
printf 'brand new\n' > "$r8/brand-new.txt"
out=$("$cp" -C "$r8" --expect-branch "$branch" --expect-sha "$sha" -m "add brand-new.txt" -- brand-new.txt 2>&1); rc=$?
check "an untracked file is auto-staged and committed" 0 'untracked' 'REFUSED|ERROR' "$out" "$rc"
if ! git -C "$r8" ls-files --error-unmatch -- brand-new.txt >/dev/null 2>&1; then
  echo "FAIL: brand-new.txt was not actually committed"
  fail=1
else
  echo "PASS: brand-new.txt landed in the commit"
fi

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
