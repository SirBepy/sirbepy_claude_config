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

# --- deterministic session-marker liveness for every test below (todo 924 REOPENED) ---
# commit-pathspec.sh's own default marker dir is the REAL hooks/.session-markers/ next to this
# checkout, which routinely holds more than one live entry (this machine runs several concurrent
# Claude Code sessions against ~/.claude). Every existing auto-derive assertion below assumes a
# SOLO session, so this suite must never read that real, shared, moving-target directory - it
# stubs COMMIT_PATHSPEC_SESSION_MARKER_DIR (the injection point added for this todo) to a private
# one-marker scratch dir by default, and overrides it per-call only for the tests further down
# that specifically exercise the 2+-marker path.
make_marker_dir() {
  local n="$1" d i
  d=$(mktemp -d) || { echo "FAIL: mktemp -d (marker dir)"; exit 1; }
  i=1
  while [ "$i" -le "$n" ]; do
    # UUID-shaped on purpose: the count filter in commit-pathspec.sh only recognises a bare
    # session-id marker, so a fake named session-$i would be skipped and every multi-session
    # assertion here would pass for the wrong reason.
    printf 'x' > "$d/$(printf '%08d' "$i")-0000-4000-8000-000000000000"
    i=$((i + 1))
  done
  # A non-marker file the filter must IGNORE, in every marker dir this suite builds: proves the
  # count is not just globbing the directory (todo 426 put precompact backups in here).
  printf 'x' > "$d/precompact-00000000-0000-4000-8000-000000000000.json"
  printf '%s' "$d"
}
solo_marker_dir=$(make_marker_dir 1)
tmp_dirs+=("$solo_marker_dir")
export COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir"

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

# --- session-marker liveness gate (todo 924 REOPENED): 2+ live markers make an auto-derived
# own-range UNVERIFIED, never "clean" - same two-separate-hunks shape as the very first test
# above (own hunk at line 3, a peer-standin hunk at line 20), the exact repro the todo recorded ---
r9=$(new_repo); tmp_dirs+=("$r9")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r9/multi.txt"
git -C "$r9" add multi.txt
git -C "$r9" commit -q -m "seed multi.txt"
branch=$(git -C "$r9" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r9" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r9/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r9/multi.txt"
multi_marker_dir=$(make_marker_dir 2)
tmp_dirs+=("$multi_marker_dir")
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r9" --expect-branch "$branch" --expect-sha "$sha" -m "should be unverified" -- multi.txt 2>&1); rc=$?
check "2+ live markers: auto-derived range is UNVERIFIED, never printed clean" \
  1 'foreign-hunk-check.*UNVERIFIED' 'foreign-hunk-check.*clean' "$out" "$rc"
if [ "$(git -C "$r9" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: an UNVERIFIED foreign-hunk-check must not have committed anything"
  fail=1
else
  echo "PASS: UNVERIFIED foreign-hunk-check left HEAD untouched"
fi
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r9" --expect-branch "$branch" --expect-sha "$sha" --force foreign-hunk -m "forced through despite peers" -- multi.txt 2>&1); rc=$?
check "--force foreign-hunk proceeds past the same UNVERIFIED auto-derived range" \
  0 'OVERRIDDEN \(--force foreign-hunk\): auto-derived own-range trusted despite 2 live session markers' 'REFUSED' "$out" "$rc"

# --- the same auto-derive path, alone in the tree (1 live marker): still commits normally, no
# extra ceremony added for the common single-session case ---
r10=$(new_repo); tmp_dirs+=("$r10")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r10/multi.txt"
git -C "$r10" add multi.txt
git -C "$r10" commit -q -m "seed multi.txt"
branch=$(git -C "$r10" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r10" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r10/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r10/multi.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r10" --expect-branch "$branch" --expect-sha "$sha" -m "solo auto-derive still commits" -- multi.txt 2>&1); rc=$?
check "exactly 1 live marker: auto-derived range is trusted, commits normally" \
  0 'auto-derived own-range 1-6,17-23 \(every current hunk assumed own' 'UNVERIFIED|REFUSED' "$out" "$rc"
if [ "$(git -C "$r10" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: solo-session commit did not land"
  fail=1
else
  echo "PASS: solo-session commit landed"
fi

# --- a caller-declared --own-range is trusted unconditionally, even with 2+ live markers ---
r11=$(new_repo); tmp_dirs+=("$r11")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r11/multi.txt"
git -C "$r11" add multi.txt
git -C "$r11" commit -q -m "seed multi.txt"
branch=$(git -C "$r11" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r11" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r11/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r11/multi.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r11" --expect-branch "$branch" --expect-sha "$sha" --own-range multi.txt:1-6,17-23 -m "declared range trusted regardless of peers" -- multi.txt 2>&1); rc=$?
check "a caller-declared --own-range is trusted under 2+ live markers, no force needed" \
  0 'caller-declared own-range 1-6,17-23' 'UNVERIFIED|REFUSED' "$out" "$rc"

# --- an untracked (brand-new) file's auto-derived range stays trusted under 2+ live markers: it
# has no HEAD baseline, so there is no pre-existing structure for a peer's lines to hide inside ---
r12=$(new_repo); tmp_dirs+=("$r12")
branch=$(git -C "$r12" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r12" rev-parse HEAD)
printf 'brand new\nsecond line\n' > "$r12/brand-new.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r12" --expect-branch "$branch" --expect-sha "$sha" -m "untracked exempt from the multi-session gate" -- brand-new.txt 2>&1); rc=$?
check "an untracked file's auto-derived range is exempt from the 2+-marker gate" \
  0 'auto-derived own-range 1-2 \(every current hunk assumed own' 'UNVERIFIED|REFUSED' "$out" "$rc"

# --- archive shape (todo 978): a pathspec carrying a DELETED source path AND an ADDED
# destination path together, in different directories (mirrors .claude/todos/<id>-*.md moving to
# .claude/todos/done/<id>-*.md) - the exact shape the coverage-check's same-directory heuristic
# cannot see (source and destination sit in different directories, so a caller who forgot the
# source half would fall into the non-blocking coverage_other warning, not coverage_move) and the
# shape a raw filesystem move (no `git rm`) leaves as a tracked-but-missing, never-staged file
# (deleted-unstaged) rather than the deleted-staged case r2 above already covers ---
r13=$(new_repo); tmp_dirs+=("$r13")
mkdir -p "$r13/todos" "$r13/todos/done"
printf 'the archived todo\n' > "$r13/todos/978-example.md"
git -C "$r13" add todos/978-example.md
git -C "$r13" commit -q -m "seed todos/978-example.md"
branch=$(git -C "$r13" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r13" rev-parse HEAD)
# A raw move, not `git mv` - matches complete-todo.ps1's Move-Item, which never touches the
# index. The source stays tracked (still in the index) but is gone from disk: deleted-unstaged.
mv "$r13/todos/978-example.md" "$r13/todos/done/978-example.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r13" --expect-branch "$branch" --expect-sha "$sha" \
  -m "archive todo 978" -- todos/978-example.md todos/done/978-example.md 2>&1); rc=$?
check "archive shape: deleted source + added destination together commits cleanly" \
  0 'todos/978-example\.md: deleted-unstaged' 'REFUSED|ERROR' "$out" "$rc"
if [ -n "$(git -C "$r13" status --porcelain)" ]; then
  echo "FAIL: archive shape - working tree not clean after the commit: $(git -C "$r13" status --porcelain)"
  fail=1
else
  echo "PASS: archive shape - working tree clean after the commit"
fi
if git -C "$r13" ls-files --error-unmatch -- todos/978-example.md >/dev/null 2>&1; then
  echo "FAIL: archive shape - the source deletion did not land (still tracked)"
  fail=1
else
  echo "PASS: archive shape - the source deletion landed"
fi
if ! git -C "$r13" ls-files --error-unmatch -- todos/done/978-example.md >/dev/null 2>&1; then
  echo "FAIL: archive shape - the destination add did not land"
  fail=1
else
  echo "PASS: archive shape - the destination add landed"
fi

# --- archive shape, forgotten source half (todo 983): naming only the destination must now be
# CAUGHT by the coverage check, not silently commit while the source rides along as an invisible
# unstaged delete. This replaces the old assertion that it "still commits" (that was the exact
# defect todo 983 fixes) - the coverage check now widens to unstaged deletions and matches by
# basename across directories, so it sees the source half and refuses before ever committing ---
r14=$(new_repo); tmp_dirs+=("$r14")
mkdir -p "$r14/todos" "$r14/todos/done"
printf 'the archived todo\n' > "$r14/todos/978-example.md"
git -C "$r14" add todos/978-example.md
git -C "$r14" commit -q -m "seed todos/978-example.md"
branch=$(git -C "$r14" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r14" rev-parse HEAD)
mv "$r14/todos/978-example.md" "$r14/todos/done/978-example.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r14" --expect-branch "$branch" --expect-sha "$sha" \
  -m "destination only, forgot the source" -- todos/done/978-example.md 2>&1); rc=$?
check "archive shape: destination-only pathspec is caught by the coverage check, names the source" \
  1 'coverage-check.*REFUSED.*todos/978-example\.md' '' "$out" "$rc"
if [ "$(git -C "$r14" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: a refused coverage-check must not have committed anything"
  fail=1
else
  echo "PASS: refused coverage-check left HEAD untouched"
fi
if git -C "$r14" ls-files --error-unmatch -- todos/978-example.md >/dev/null 2>&1; then
  echo "PASS: forgotten-source case - source deletion left uncommitted and visible in git status, not silently dropped"
else
  echo "FAIL: forgotten-source case - source path vanished from the index entirely (should still be tracked, just deleted on disk)"
  fail=1
fi
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r14" --expect-branch "$branch" --expect-sha "$sha" \
  --force coverage -m "destination only, forced through" -- todos/done/978-example.md 2>&1); rc=$?
check "--force coverage proceeds past the same forgotten-source hit" \
  0 'OVERRIDDEN \(--force coverage\).*todos/978-example\.md' 'REFUSED' "$out" "$rc"
if [ -z "$(git -C "$r14" status --porcelain -- todos/978-example.md)" ]; then
  echo "FAIL: forgotten-source case - git status shows nothing for the un-pathspec'd deletion after forcing through (it should show as a pending unstaged delete)"
  fail=1
else
  echo "PASS: forgotten-source case - git status still shows the pending unstaged delete after forcing through, confirming --force coverage does not silently fix it for the caller either"
fi

# --- unrelated STAGED deletion (todo 983 regression guard): another session's own staged delete,
# unrelated directory AND unrelated basename to anything in THIS pathspec, must stay a
# non-blocking warning - refusing here would brick /commit for every concurrent session sharing
# this checkout, which is the exact regression the coverage check must never introduce ---
r17=$(new_repo); tmp_dirs+=("$r17")
mkdir -p "$r17/peer-dir"
printf 'peer content\n' > "$r17/peer-dir/unrelated-peer-file.txt"
printf 'my content\n' > "$r17/mine.txt"
git -C "$r17" add peer-dir/unrelated-peer-file.txt mine.txt
git -C "$r17" commit -q -m "seed peer file + mine.txt"
branch=$(git -C "$r17" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r17" rev-parse HEAD)
git -C "$r17" rm -q peer-dir/unrelated-peer-file.txt
printf 'my content EDITED\n' > "$r17/mine.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r17" --expect-branch "$branch" --expect-sha "$sha" \
  -m "edit mine.txt, unrelated staged delete alongside it" -- mine.txt 2>&1); rc=$?
check "an unrelated STAGED deletion (different dir, different basename) only warns, never refuses" \
  0 'coverage-check.*warning, non-blocking.*peer-dir/unrelated-peer-file\.txt' 'coverage-check.*REFUSED' "$out" "$rc"
if [ "$(git -C "$r17" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: the unrelated-staged-deletion case did not commit mine.txt"
  fail=1
else
  echo "PASS: the unrelated-staged-deletion case committed mine.txt despite the peer's staged delete"
fi

# --- unrelated UNSTAGED deletion (todo 983 regression guard): another session's raw filesystem
# delete of a tracked file it never staged - unrelated directory AND unrelated basename - must
# also stay a non-blocking warning. This is the exact new READ path this todo adds (unstaged
# `git diff --name-status`), so it is the case most likely for a careless fix to turn into a
# refusal by accident ---
r18=$(new_repo); tmp_dirs+=("$r18")
mkdir -p "$r18/other-peer-dir"
printf 'peer content\n' > "$r18/other-peer-dir/leftover.txt"
printf 'my content\n' > "$r18/mine.txt"
git -C "$r18" add other-peer-dir/leftover.txt mine.txt
git -C "$r18" commit -q -m "seed peer leftover + mine.txt"
branch=$(git -C "$r18" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r18" rev-parse HEAD)
rm "$r18/other-peer-dir/leftover.txt"
printf 'my content EDITED\n' > "$r18/mine.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r18" --expect-branch "$branch" --expect-sha "$sha" \
  -m "edit mine.txt, unrelated unstaged delete alongside it" -- mine.txt 2>&1); rc=$?
check "an unrelated UNSTAGED deletion (different dir, different basename) only warns, never refuses" \
  0 'coverage-check.*warning, non-blocking.*other-peer-dir/leftover\.txt' 'coverage-check.*REFUSED' "$out" "$rc"
if [ "$(git -C "$r18" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: the unrelated-unstaged-deletion case did not commit mine.txt"
  fail=1
else
  echo "PASS: the unrelated-unstaged-deletion case committed mine.txt despite the peer's unstaged delete"
fi
if ! git -C "$r18" ls-files --error-unmatch -- other-peer-dir/leftover.txt >/dev/null 2>&1; then
  echo "FAIL: the peer's unrelated unstaged delete must not have been touched by this commit at all"
  fail=1
else
  echo "PASS: the peer's unrelated unstaged delete is untouched (still tracked, just missing on disk, exactly as the peer left it)"
fi

# --- --own-since fixture: seed, then two "own" commits touching the same file, mirroring a
# session that committed twice before reaching for commit-pathspec.sh a third time. A fresh
# instance is built per scenario below rather than reusing one repo across several committing
# calls, so an earlier scenario's real commit never drifts the next scenario's --expect-sha.
make_own_since_fixture() {
  local d
  d=$(new_repo)
  printf 'seed\n' > "$d/own-since.txt"
  git -C "$d" add own-since.txt
  git -C "$d" commit -q -m "seed own-since.txt"
  printf '%s' "$d"
}

# --- --own-since: resolves <sha>..HEAD into the same sha list --own accepts, removing the
# retyped `git log --format=%H <session-start>..HEAD` substitution (todo 978) ---
r15=$(make_own_since_fixture); tmp_dirs+=("$r15")
since_sha=$(git -C "$r15" rev-parse HEAD)
branch=$(git -C "$r15" rev-parse --abbrev-ref HEAD)
printf 'seed\ncommit one\n' > "$r15/own-since.txt"
git -C "$r15" commit -q -am "own commit one"
commit_one=$(git -C "$r15" rev-parse HEAD)
printf 'seed\ncommit one\ncommit two\n' > "$r15/own-since.txt"
git -C "$r15" commit -q -am "own commit two"
sha=$(git -C "$r15" rev-parse HEAD)
commit_two=$(git -C "$r15" rev-parse HEAD)
printf 'seed\ncommit one\ncommit two\nworking tree edit\n' > "$r15/own-since.txt"
# `git log --format=%H a..b` lists newest first, so commit two (== HEAD) precedes commit one.
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r15" --expect-branch "$branch" --expect-sha "$sha" \
  --own-since "$since_sha" -m "own-since resolves the sha list" -- own-since.txt 2>&1); rc=$?
check "--own-since resolves <sha>..HEAD to the 2 commits actually made since it" \
  0 "own-since. resolved $since_sha..HEAD to 2 commit\(s\): $commit_two,$commit_one" 'REFUSED' "$out" "$rc"

# --- --own-since: an invalid ref is a usage error (exit 2), not a silent no-op - a fresh fixture
# so an earlier scenario's real commit can never be mistaken for one this call made ---
r15b=$(make_own_since_fixture); tmp_dirs+=("$r15b")
since_sha_b=$(git -C "$r15b" rev-parse HEAD)
branch_b=$(git -C "$r15b" rev-parse --abbrev-ref HEAD)
printf 'seed\ncommit one\n' > "$r15b/own-since.txt"
git -C "$r15b" commit -q -am "own commit one"
printf 'seed\ncommit one\ncommit two\n' > "$r15b/own-since.txt"
git -C "$r15b" commit -q -am "own commit two"
sha_b=$(git -C "$r15b" rev-parse HEAD)
printf 'seed\ncommit one\ncommit two\nworking tree edit\n' > "$r15b/own-since.txt"
out=$("$cp" -C "$r15b" --expect-branch "$branch_b" --expect-sha "$sha_b" \
  --own-since "not-a-real-sha" -m "should not run" -- own-since.txt 2>&1); rc=$?
check "--own-since with an unresolvable ref exits 2, not silently ignored" \
  2 'does not resolve to a commit' '' "$out" "$rc"
if [ "$(git -C "$r15b" rev-parse HEAD)" != "$sha_b" ]; then
  echo "FAIL: an ERROR exit from bad --own-since must not have committed anything"
  fail=1
else
  echo "PASS: bad --own-since left HEAD untouched"
fi

# --- --own-since: the foreign-hunk own-range for a file changed across the SINCE commits plus
# the current working tree is derived from that wider baseline and TRUSTED regardless of live
# session-marker count (todo 978) - stronger evidence than the HEAD-only auto-derive, which the
# same 2+-marker dir makes UNVERIFIED (proven above by r9). This is the interaction the todo asks
# to be resolved and documented: --own-since satisfies the gate the way a declared --own-range
# does, because the range traces to a concrete, git-verifiable commit list rather than "whatever
# is uncommitted right now" - a fresh fixture again, since this scenario also commits ---
r15c=$(make_own_since_fixture); tmp_dirs+=("$r15c")
since_sha_c=$(git -C "$r15c" rev-parse HEAD)
branch_c=$(git -C "$r15c" rev-parse --abbrev-ref HEAD)
printf 'seed\ncommit one\n' > "$r15c/own-since.txt"
git -C "$r15c" commit -q -am "own commit one"
printf 'seed\ncommit one\ncommit two\n' > "$r15c/own-since.txt"
git -C "$r15c" commit -q -am "own commit two"
sha_c=$(git -C "$r15c" rev-parse HEAD)
printf 'seed\ncommit one\ncommit two\nworking tree edit\n' > "$r15c/own-since.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r15c" --expect-branch "$branch_c" --expect-sha "$sha_c" \
  --own-since "$since_sha_c" -m "own-since bypasses the multi-session gate" -- own-since.txt 2>&1); rc=$?
check "--own-since's wider baseline is trusted under 2+ live markers, no --force needed" \
  0 'derived since '"$since_sha_c"', trusted - own commit history, todo 978' 'UNVERIFIED|REFUSED' "$out" "$rc"
new_head=$(git -C "$r15c" rev-parse HEAD)
if [ "$new_head" = "$sha_c" ]; then
  echo "FAIL: --own-since commit under 2+ markers did not land"
  fail=1
else
  echo "PASS: --own-since commit under 2+ markers landed"
fi

# --- --own-since: the plain --own form is unchanged - passing an (unrelated, unreachable) sha
# via --own alongside the ordinary HEAD-relative auto-derive still produces the exact same
# auto-derive verdict as the very first test in this suite, proving --own-since's new merge logic
# never runs when --own-since itself is absent ---
r16=$(new_repo); tmp_dirs+=("$r16")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r16/multi.txt"
git -C "$r16" add multi.txt
git -C "$r16" commit -q -m "seed multi.txt"
branch=$(git -C "$r16" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r16" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r16/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r16/multi.txt"
unrelated_sha=$(git -C "$r16" rev-parse HEAD)
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r16" --expect-branch "$branch" --expect-sha "$sha" \
  --own "$unrelated_sha" -m "edit two hunks, plain --own untouched" -- multi.txt 2>&1); rc=$?
check "plain --own (no --own-since) still leaves the HEAD-relative auto-derive unchanged" \
  0 'auto-derived own-range 1-6,17-23 \(every current hunk assumed own' 'derived since|UNVERIFIED|REFUSED' "$out" "$rc"

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
