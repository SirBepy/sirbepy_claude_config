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

# --- repeated --force flags accumulate, never last-one-wins (todo 1053): a stale HEAD plus an
# undeclared second hunk in the same call, overridden with two SEPARATE --force flags rather
# than one comma-joined value - proves the arg parser appends instead of overwriting ---
r19=$(new_repo); tmp_dirs+=("$r19")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r19/multi.txt"
git -C "$r19" add multi.txt
git -C "$r19" commit -q -m "seed multi.txt"
branch=$(git -C "$r19" rev-parse --abbrev-ref HEAD)
stale_sha=$(git -C "$r19" rev-parse HEAD)
printf 'peer commit\n' >> "$r19/README.md"
git -C "$r19" commit -q -am "simulated peer commit, unrelated file"
sed -i '3s/.*/line 03 CHANGED/' "$r19/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r19/multi.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r19" --expect-branch "$branch" --expect-sha "$stale_sha" \
  --own-range multi.txt:1-6 --force head-guard --force foreign-hunk -m "repeated force accumulates" -- multi.txt 2>&1); rc=$?
check "repeated --force head-guard: overridden rather than lost to a later --force" \
  0 'OVERRIDDEN \(--force head-guard\)' 'REFUSED' "$out" "$rc"
check "repeated --force foreign-hunk: ALSO overridden in the same call (todo 1053)" \
  0 'OVERRIDDEN \(--force foreign-hunk\)' 'REFUSED' "$out" "$rc"

# --- overlap-check on a personal-repo origin proceeds without --force (todo 1076): a local
# bare remote stands in for "has an upstream" without needing network access, then the
# origin url decides personal vs client exactly as hooks/gh-account-switch.sh's own mapping
# does. Unpushed commit changes line 5; the working tree edits line 5 again - a real
# hunk-level overlap, not file-level ---
r20=$(new_repo); tmp_dirs+=("$r20")
bare20=$(mktemp -d) || { echo "FAIL: mktemp -d (bare20)"; exit 1; }
tmp_dirs+=("$bare20")
git init -q --bare "$bare20"
git -C "$r20" remote add origin "$bare20"
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r20/multi.txt"
git -C "$r20" add multi.txt
git -C "$r20" commit -q -m "seed multi.txt"
branch=$(git -C "$r20" rev-parse --abbrev-ref HEAD)
git -C "$r20" push -q -u origin "$branch"
sed -i '5s/.*/line 05 UNPUSHED/' "$r20/multi.txt"
git -C "$r20" commit -q -am "unpushed change to line 5"
sha=$(git -C "$r20" rev-parse HEAD)
sed -i '5s/.*/line 05 WORKING TREE EDIT/' "$r20/multi.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r20" --expect-branch "$branch" --expect-sha "$sha" \
  -m "personal repo proceeds on overlap without force" -- multi.txt 2>&1); rc=$?
check "personal-repo origin: an overlap hit proceeds without --force, prints the info line" \
  0 'personal repo: proceeding \(SKILL.md step 8 branch 2\)' 'REFUSED' "$out" "$rc"
if [ "$(git -C "$r20" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: personal-repo overlap bypass did not commit"
  fail=1
else
  echo "PASS: personal-repo overlap bypass committed"
fi

# --- the same overlap hit on a client-repo origin still refuses by default (todo 1076) - the
# origin is changed to a client-org url AFTER the local push, since @{u} only needs the
# already-fetched tracking ref, not a reachable remote ---
r21=$(new_repo); tmp_dirs+=("$r21")
bare21=$(mktemp -d) || { echo "FAIL: mktemp -d (bare21)"; exit 1; }
tmp_dirs+=("$bare21")
git init -q --bare "$bare21"
git -C "$r21" remote add origin "$bare21"
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r21/multi.txt"
git -C "$r21" add multi.txt
git -C "$r21" commit -q -m "seed multi.txt"
branch=$(git -C "$r21" rev-parse --abbrev-ref HEAD)
git -C "$r21" push -q -u origin "$branch"
sed -i '5s/.*/line 05 UNPUSHED/' "$r21/multi.txt"
git -C "$r21" commit -q -am "unpushed change to line 5"
sha=$(git -C "$r21" rev-parse HEAD)
sed -i '5s/.*/line 05 WORKING TREE EDIT/' "$r21/multi.txt"
git -C "$r21" remote set-url origin "https://github.com/zirtue-corp/testrepo.git"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r21" --expect-branch "$branch" --expect-sha "$sha" \
  -m "client repo still refuses on overlap" -- multi.txt 2>&1); rc=$?
check "client-repo origin: an overlap hit still refuses by default" \
  1 'overlap-check.*REFUSED' 'personal repo: proceeding' "$out" "$rc"
check "client-repo overlap REFUSED message names a --force value the script actually accepts" \
  1 'REFUSED.*--force overlap' '' "$out" "$rc"
if [ "$(git -C "$r21" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: a refused client-repo overlap must not have committed"
  fail=1
else
  echo "PASS: refused client-repo overlap left HEAD untouched"
fi

# --- --force overlap-check is accepted as an alias for --force overlap (todo 1076) - the
# label the REFUSED message itself prints, which a caller naturally retypes verbatim ---
r22=$(new_repo); tmp_dirs+=("$r22")
bare22=$(mktemp -d) || { echo "FAIL: mktemp -d (bare22)"; exit 1; }
tmp_dirs+=("$bare22")
git init -q --bare "$bare22"
git -C "$r22" remote add origin "$bare22"
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r22/multi.txt"
git -C "$r22" add multi.txt
git -C "$r22" commit -q -m "seed multi.txt"
branch=$(git -C "$r22" rev-parse --abbrev-ref HEAD)
git -C "$r22" push -q -u origin "$branch"
sed -i '5s/.*/line 05 UNPUSHED/' "$r22/multi.txt"
git -C "$r22" commit -q -am "unpushed change to line 5"
sha=$(git -C "$r22" rev-parse HEAD)
sed -i '5s/.*/line 05 WORKING TREE EDIT/' "$r22/multi.txt"
git -C "$r22" remote set-url origin "https://github.com/zirtue-corp/testrepo.git"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r22" --expect-branch "$branch" --expect-sha "$sha" \
  --force overlap-check -m "overlap-check alias accepted" -- multi.txt 2>&1); rc=$?
check "--force overlap-check is accepted as an alias for --force overlap" \
  0 'OVERRIDDEN \(--force overlap\)' 'REFUSED' "$out" "$rc"

# --- coverage check: a staged MODIFY to an unrelated, same-basename file in a different
# directory must only WARN, never REFUSE (todo 1073) - the false positive was the staged-diff
# loop calling check_coverage_hit for every status, not only a deletion/rename, so a same-
# basename M status (still fully present, nothing missing) got treated as "half a move" ---
r28=$(new_repo); tmp_dirs+=("$r28")
mkdir -p "$r28/a" "$r28/b"
printf 'a-content\n' > "$r28/a/config.yml"
printf 'b-content\n' > "$r28/b/config.yml"
git -C "$r28" add a/config.yml b/config.yml
git -C "$r28" commit -q -m "seed a/config.yml b/config.yml"
branch=$(git -C "$r28" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r28" rev-parse HEAD)
printf 'a-content EDITED\n' > "$r28/a/config.yml"
git -C "$r28" add a/config.yml
printf 'b-content EDITED\n' > "$r28/b/config.yml"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r28" --expect-branch "$branch" --expect-sha "$sha" \
  -m "unrelated same-basename staged edit only warns" -- b/config.yml 2>&1); rc=$?
check "a staged MODIFY to an unrelated same-basename file only warns, never refuses (todo 1073)" \
  0 'coverage-check.*warning, non-blocking.*a/config\.yml' 'coverage-check.*REFUSED' "$out" "$rc"
if [ "$(git -C "$r28" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: the same-basename-modify case did not commit b/config.yml"
  fail=1
else
  echo "PASS: the same-basename-modify case committed b/config.yml despite the unrelated staged edit"
fi

# --- coverage check regression guard: a REAL git mv across directories with the SAME
# basename, destination only in the pathspec, still refuses (todo 1073 must not regress the
# todo-983 archival-move case the basename rule exists for) ---
r27=$(new_repo); tmp_dirs+=("$r27")
mkdir -p "$r27/x" "$r27/y"
printf 'moved content\n' > "$r27/x/f.md"
git -C "$r27" add x/f.md
git -C "$r27" commit -q -m "seed x/f.md"
branch=$(git -C "$r27" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r27" rev-parse HEAD)
git -C "$r27" mv x/f.md y/f.md
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r27" --expect-branch "$branch" --expect-sha "$sha" \
  -m "same-basename real rename, destination only" -- y/f.md 2>&1); rc=$?
check "same-basename rename across directories (real git mv) still refuses when only destination is named" \
  1 'coverage-check.*REFUSED.*x/f\.md' '' "$out" "$rc"

# --- foreign-hunk-check liveness filter (todo 985): a marker whose registered cwd (via
# ~/.claude/sessions/*.json, COMMIT_PATHSPEC_SESSION_REGISTRY_DIR overridden here) is a
# DIFFERENT repo cannot hold a hunk in THIS one, so it must not count toward the 2+-marker
# gate - leaving a genuinely solo session free of the UNVERIFIED refusal just because other
# Claude sessions are live elsewhere on the machine ---
r25=$(new_repo); tmp_dirs+=("$r25")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r25/multi.txt"
git -C "$r25" add multi.txt
git -C "$r25" commit -q -m "seed multi.txt"
branch=$(git -C "$r25" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r25" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r25/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r25/multi.txt"
marker_dir25=$(mktemp -d); tmp_dirs+=("$marker_dir25")
registry_dir25=$(mktemp -d); tmp_dirs+=("$registry_dir25")
unrelated_dir25=$(mktemp -d); tmp_dirs+=("$unrelated_dir25")
same_id25="11111111-1111-4111-8111-111111111111"
other_id25="22222222-2222-4222-8222-222222222222"
printf 'x' > "$marker_dir25/$same_id25"
printf 'x' > "$marker_dir25/$other_id25"
repo25_root=$(git -C "$r25" rev-parse --show-toplevel)
printf '{"pid":1,"sessionId":"%s","cwd":"%s"}' "$same_id25" "$repo25_root" > "$registry_dir25/same.json"
printf '{"pid":2,"sessionId":"%s","cwd":"%s"}' "$other_id25" "$unrelated_dir25" > "$registry_dir25/other.json"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$marker_dir25" COMMIT_PATHSPEC_SESSION_REGISTRY_DIR="$registry_dir25" \
  "$cp" -C "$r25" --expect-branch "$branch" --expect-sha "$sha" -m "only the same-repo marker counts" -- multi.txt 2>&1); rc=$?
check "a marker registered to a DIFFERENT repo's cwd is not counted, leaving this session solo (todo 985)" \
  0 'auto-derived own-range 1-6,17-23 \(every current hunk assumed own' 'UNVERIFIED|REFUSED' "$out" "$rc"

# --- same filter, regression guard: two markers BOTH registered to THIS repo's cwd still
# trigger the UNVERIFIED gate - proves the repo-scoping does not just silence the check ---
r26=$(new_repo); tmp_dirs+=("$r26")
{
  printf 'line %02d\n' $(seq 1 30)
} > "$r26/multi.txt"
git -C "$r26" add multi.txt
git -C "$r26" commit -q -m "seed multi.txt"
branch=$(git -C "$r26" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r26" rev-parse HEAD)
sed -i '3s/.*/line 03 CHANGED/' "$r26/multi.txt"
sed -i '20s/.*/line 20 CHANGED/' "$r26/multi.txt"
marker_dir26=$(mktemp -d); tmp_dirs+=("$marker_dir26")
registry_dir26=$(mktemp -d); tmp_dirs+=("$registry_dir26")
peer_id26="33333333-3333-4333-8333-333333333333"
own_id26="44444444-4444-4444-8444-444444444444"
printf 'x' > "$marker_dir26/$peer_id26"
printf 'x' > "$marker_dir26/$own_id26"
repo26_root=$(git -C "$r26" rev-parse --show-toplevel)
printf '{"pid":3,"sessionId":"%s","cwd":"%s"}' "$peer_id26" "$repo26_root" > "$registry_dir26/peer.json"
printf '{"pid":4,"sessionId":"%s","cwd":"%s"}' "$own_id26" "$repo26_root" > "$registry_dir26/own.json"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$marker_dir26" COMMIT_PATHSPEC_SESSION_REGISTRY_DIR="$registry_dir26" \
  "$cp" -C "$r26" --expect-branch "$branch" --expect-sha "$sha" -m "two same-repo markers still refuse" -- multi.txt 2>&1); rc=$?
check "two markers both registered to THIS repo's cwd still trigger UNVERIFIED (todo 985)" \
  1 'foreign-hunk-check.*UNVERIFIED' 'foreign-hunk-check.*clean' "$out" "$rc"

# --- a short --expect-sha resolves via git rev-parse before the head-guard comparison (todo
# 994, script half) instead of a bare string-equality that could only ever match a full sha ---
r24=$(new_repo); tmp_dirs+=("$r24")
branch=$(git -C "$r24" rev-parse --abbrev-ref HEAD)
full_sha24=$(git -C "$r24" rev-parse HEAD)
short_sha24="${full_sha24:0:7}"
printf 'seed\nedited\n' > "$r24/README.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r24" --expect-branch "$branch" --expect-sha "$short_sha24" \
  -m "short expect-sha resolves before comparing" -- README.md 2>&1); rc=$?
check "a short --expect-sha resolves to the full sha before the head-guard comparison" \
  0 'head-guard. OK' 'REFUSED|ERROR' "$out" "$rc"

# --- untracked-file exemption keys on "no blob at HEAD", not on classify_path's live/
# untracked split (todo 1026): a brand-new file the caller already `git add`-ed before calling
# this script is "live" per classify_path (it's in the index now), but it still has no HEAD
# baseline for a peer's lines to hide inside, so it must stay exempt from the 2+-marker gate
# exactly like a never-added untracked file does ---
r23=$(new_repo); tmp_dirs+=("$r23")
branch=$(git -C "$r23" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r23" rev-parse HEAD)
printf 'brand new\nsecond line\n' > "$r23/brand-new.txt"
git -C "$r23" add brand-new.txt
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$multi_marker_dir" "$cp" -C "$r23" --expect-branch "$branch" --expect-sha "$sha" \
  -m "pre-added new file keeps the untracked exemption" -- brand-new.txt 2>&1); rc=$?
check "a pre-git-add'ed new file (no HEAD blob) stays exempt from the 2+-marker gate (todo 1026)" \
  0 'auto-derived own-range 1-2 \(every current hunk assumed own' 'UNVERIFIED|REFUSED' "$out" "$rc"

# --- coverage-basename-new-file: the same-basename rule (todo 983's archival heuristic) must
# only fire when the PATHSPEC file itself is new (a move's destination always is) - an unrelated
# deletion elsewhere that merely happens to share a basename with an EXISTING, modified pathspec
# file is not "half of a move" the way a brand-new same-basename destination is, since the
# pathspec file already had its own HEAD blob before this commit touched it ---
r29=$(new_repo); tmp_dirs+=("$r29")
mkdir -p "$r29/skills/foo" "$r29/skills/bar"
printf 'foo content\n' > "$r29/skills/foo/SKILL.md"
printf 'bar content\n' > "$r29/skills/bar/SKILL.md"
git -C "$r29" add skills/foo/SKILL.md skills/bar/SKILL.md
git -C "$r29" commit -q -m "seed skills/foo and skills/bar"
branch=$(git -C "$r29" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r29" rev-parse HEAD)
printf 'foo content EDITED\n' > "$r29/skills/foo/SKILL.md"
rm "$r29/skills/bar/SKILL.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r29" --expect-branch "$branch" --expect-sha "$sha" \
  -m "edit an existing same-basename file, unrelated deletion pending elsewhere" -- skills/foo/SKILL.md 2>&1); rc=$?
check "an existing (non-new) pathspec file is never caught by the same-basename move heuristic" \
  0 'coverage-check.*warning, non-blocking.*skills/bar/SKILL\.md' 'coverage-check.*REFUSED' "$out" "$rc"
if [ "$(git -C "$r29" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: coverage-basename-new-file - the edit to skills/foo/SKILL.md did not commit"
  fail=1
else
  echo "PASS: coverage-basename-new-file - the edit to skills/foo/SKILL.md committed despite the unrelated same-basename deletion"
fi

# --- a working-tree deletion (never `git rm`'d, classify_path's deleted-unstaged) is excluded
# from overlap-check/foreign-hunk-check exactly like an already-`git rm`'d deleted-staged path -
# both have nothing left in the working tree to diff, so the classification line's exclusion
# note must name both, not only the git-rm case (todo 1033 item 2) ---
r30=$(new_repo); tmp_dirs+=("$r30")
mkdir -p "$r30/todos" "$r30/todos/done"
printf 'the archived todo\n' > "$r30/todos/1033-example.md"
git -C "$r30" add todos/1033-example.md
git -C "$r30" commit -q -m "seed todos/1033-example.md"
branch=$(git -C "$r30" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r30" rev-parse HEAD)
mv "$r30/todos/1033-example.md" "$r30/todos/done/1033-example.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r30" --expect-branch "$branch" --expect-sha "$sha" \
  -m "archive todo 1033" -- todos/1033-example.md todos/done/1033-example.md 2>&1); rc=$?
check "a working-tree (never git-rm'd) deletion is excluded from overlap-check/foreign-hunk-check same as a git-rm'd one" \
  0 'todos/1033-example\.md: deleted-unstaged \(excluded from overlap-check/foreign-hunk-check - nothing left to diff\)' 'REFUSED' "$out" "$rc"

# --- directory pathspec expansion (todo 1101): naming an already-tracked directory in the
# pathspec must not silently drop brand-new untracked files sitting inside it - the previous
# defect committed only the tracked modification and printed "[commit] committed" with the new
# file still `??`. Both the modified tracked file and the new file must land ---
r31=$(new_repo); tmp_dirs+=("$r31")
mkdir -p "$r31/mydir"
printf 'tracked content\n' > "$r31/mydir/tracked.txt"
git -C "$r31" add mydir/tracked.txt
git -C "$r31" commit -q -m "seed mydir/tracked.txt"
branch=$(git -C "$r31" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r31" rev-parse HEAD)
printf 'tracked content EDITED\n' > "$r31/mydir/tracked.txt"
printf 'brand new in dir\n' > "$r31/mydir/newfile.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r31" --expect-branch "$branch" --expect-sha "$sha" \
  -m "dir pathspec with modified + new file" -- mydir 2>&1); rc=$?
check "a tracked-directory pathspec expands to list the new untracked file inside it (todo 1101)" \
  0 'mydir/newfile\.txt: untracked' 'REFUSED|ERROR' "$out" "$rc"
if [ "$(git -C "$r31" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: todo 1101 - dir-pathspec commit did not land"
  fail=1
else
  echo "PASS: todo 1101 - dir-pathspec commit landed"
fi
if ! git -C "$r31" ls-files --error-unmatch -- mydir/newfile.txt >/dev/null 2>&1; then
  echo "FAIL: todo 1101 - new file inside the tracked-dir pathspec was not committed"
  fail=1
else
  echo "PASS: todo 1101 - new file inside the tracked-dir pathspec landed in the commit"
fi
if [ "$(git -C "$r31" show HEAD:mydir/tracked.txt)" != "tracked content EDITED" ]; then
  echo "FAIL: todo 1101 - the modified tracked file inside the dir pathspec did not land"
  fail=1
else
  echo "PASS: todo 1101 - the modified tracked file inside the dir pathspec landed"
fi

# --- regression guard: a WHOLLY untracked directory named as a pathspec entry keeps its
# existing behaviour (the whole directory is staged and committed via the untracked-classify
# path, unchanged by the todo-1101 expansion which only triggers for an already-tracked dir) ---
r32=$(new_repo); tmp_dirs+=("$r32")
mkdir -p "$r32/freshdir"
printf 'all new\n' > "$r32/freshdir/a.txt"
printf 'also new\n' > "$r32/freshdir/b.txt"
branch=$(git -C "$r32" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r32" rev-parse HEAD)
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r32" --expect-branch "$branch" --expect-sha "$sha" \
  -m "wholly untracked dir, unchanged behaviour" -- freshdir 2>&1); rc=$?
check "a wholly untracked directory pathspec still commits every file inside it (regression guard)" \
  0 'freshdir: untracked' 'REFUSED|ERROR' "$out" "$rc"
if ! git -C "$r32" ls-files --error-unmatch -- freshdir/a.txt freshdir/b.txt >/dev/null 2>&1; then
  echo "FAIL: regression guard - a wholly untracked directory no longer commits all its files"
  fail=1
else
  echo "PASS: regression guard - a wholly untracked directory still commits all its files"
fi

# --- a non-ASCII new file inside a tracked-directory pathspec: git quotes such paths
# ("d/\304\215vor.txt") unless core.quotePath is off, and a quoted name cannot be staged,
# which used to abort the whole commit ---
r33=$(new_repo); tmp_dirs+=("$r33")
mkdir -p "$r33/d"
printf 'tracked\n' > "$r33/d/t.txt"
git -C "$r33" add d/t.txt
git -C "$r33" commit -q -m "seed d/t.txt"
branch=$(git -C "$r33" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r33" rev-parse HEAD)
printf 'tracked EDITED\n' > "$r33/d/t.txt"
printf 'novo\n' > "$r33/d/čvor.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r33" --expect-branch "$branch" --expect-sha "$sha" \
  -m "dir pathspec with a non-ASCII new file" -- d 2>&1); rc=$?
check "a non-ASCII new file inside a tracked-directory pathspec commits (unquoted path)" \
  0 'd/čvor\.txt: untracked' 'REFUSED|ERROR' "$out" "$rc"
if ! git -C "$r33" -c core.quotePath=false ls-files --error-unmatch -- "d/čvor.txt" >/dev/null 2>&1; then
  echo "FAIL: the non-ASCII new file inside the tracked-dir pathspec was not committed"
  fail=1
else
  echo "PASS: the non-ASCII new file inside the tracked-dir pathspec landed"
fi

# --- repeated -m accumulates into subject + body, never last-one-wins (todo 1109): git joins
# separate -m values as paragraphs, so the FIRST lands as %s (subject) and the SECOND as %b
# (body) - the defect was an assignment that kept only the last one, landing the body text as
# the subject and losing the real subject entirely ---
r34=$(new_repo); tmp_dirs+=("$r34")
branch=$(git -C "$r34" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r34" rev-parse HEAD)
printf 'two message file\n' > "$r34/two-m.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r34" --expect-branch "$branch" --expect-sha "$sha" \
  -m "subject line" -m "body paragraph" -- two-m.txt 2>&1); rc=$?
check "two -m flags commit cleanly" 0 '\[commit\] committed' 'REFUSED|ERROR' "$out" "$rc"
new_subject=$(git -C "$r34" log -1 --format=%s)
new_body=$(git -C "$r34" log -1 --format=%b)
if [ "$new_subject" = "subject line" ]; then
  echo "PASS: repeated -m (todo 1109) - subject landed as the first -m value"
else
  echo "FAIL: repeated -m (todo 1109) - subject is '$new_subject', want 'subject line'"
  fail=1
fi
if [ "$new_body" = "body paragraph" ]; then
  echo "PASS: repeated -m (todo 1109) - body landed as the second -m value"
else
  echo "FAIL: repeated -m (todo 1109) - body is '$new_body', want 'body paragraph'"
  fail=1
fi

# --- CRLF/LF conversion warning never prints from this script's own internal git calls, and
# the commit still lands with every verdict line intact (todo 1115): new_repo()'s own
# `core.autocrlf false` exists specifically so every fixture ABOVE this one never hits this
# warning, so this test builds a dedicated autocrlf=true repo - the exact setting that makes a
# plain `git diff` on a tracked, edited file print "LF will be replaced by CRLF" ---
r35=$(mktemp -d) || { echo "FAIL: mktemp -d (r35)"; exit 1; }
tmp_dirs+=("$r35")
git -C "$r35" init -q
git -C "$r35" config user.email "test@example.com"
git -C "$r35" config user.name "test"
git -C "$r35" config core.autocrlf true
printf 'line1\nline2\n' > "$r35/f.txt"
git -C "$r35" add f.txt
git -C "$r35" commit -q -m seed
branch=$(git -C "$r35" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r35" rev-parse HEAD)
printf 'line1\nline2 EDITED\n' > "$r35/f.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r35" --expect-branch "$branch" --expect-sha "$sha" \
  -m "autocrlf repo, no CRLF warning expected" -- f.txt 2>&1); rc=$?
check "commit-pathspec.sh prints no LF/CRLF conversion warning in an autocrlf repo" \
  0 '\[commit\] committed' 'will be replaced by CRLF|will be replaced by LF' "$out" "$rc"
if [ "$(git -C "$r35" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: todo 1115 - the autocrlf commit did not land"
  fail=1
else
  echo "PASS: todo 1115 - the autocrlf commit landed despite the suppressed warning class"
fi

# --- --todo <id> appends a TRACKED todo's archive-move paths by itself (todo 1105): both the
# done/ destination (filesystem glob, since complete-todo.ps1's Move-Item never stages anything)
# and the still-tracked source deletion land, with no coverage refusal and no pathspec typed by
# hand beyond `--` itself ---
r36=$(new_repo); tmp_dirs+=("$r36")
mkdir -p "$r36/.claude/todos/done"
printf 'the archived todo\n' > "$r36/.claude/todos/1105-example.md"
git -C "$r36" add .claude/todos/1105-example.md
git -C "$r36" commit -q -m "seed .claude/todos/1105-example.md"
branch=$(git -C "$r36" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r36" rev-parse HEAD)
mv "$r36/.claude/todos/1105-example.md" "$r36/.claude/todos/done/1105-example.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r36" --expect-branch "$branch" --expect-sha "$sha" \
  --todo 1105 -m "archive todo 1105 via --todo" -- 2>&1); rc=$?
check "--todo on a tracked todo commits both the done/ destination and the source deletion" \
  0 '\[commit\] committed' 'REFUSED|ERROR' "$out" "$rc"
if git -C "$r36" ls-files --error-unmatch -- .claude/todos/1105-example.md >/dev/null 2>&1; then
  echo "FAIL: --todo (tracked) - the source deletion did not land"
  fail=1
else
  echo "PASS: --todo (tracked) - the source deletion landed"
fi
if ! git -C "$r36" ls-files --error-unmatch -- .claude/todos/done/1105-example.md >/dev/null 2>&1; then
  echo "FAIL: --todo (tracked) - the done/ destination did not land"
  fail=1
else
  echo "PASS: --todo (tracked) - the done/ destination landed"
fi

# --- --todo <id> on an UNTRACKED todo (a peer-filed todo never committed) appends only the
# done/ destination - there is no tracked source to delete, so `git ls-files` finds nothing and
# this must not error or invent a path ---
r37=$(new_repo); tmp_dirs+=("$r37")
branch=$(git -C "$r37" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r37" rev-parse HEAD)
mkdir -p "$r37/.claude/todos/done"
printf 'untracked todo\n' > "$r37/.claude/todos/1106-untracked.md"
mv "$r37/.claude/todos/1106-untracked.md" "$r37/.claude/todos/done/1106-untracked.md"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r37" --expect-branch "$branch" --expect-sha "$sha" \
  --todo 1106 -m "archive untracked todo 1106 via --todo" -- 2>&1); rc=$?
check "--todo on an untracked todo commits only the done/ destination" \
  0 '\.claude/todos/done/1106-untracked\.md: untracked' 'REFUSED|ERROR' "$out" "$rc"
if ! git -C "$r37" ls-files --error-unmatch -- .claude/todos/done/1106-untracked.md >/dev/null 2>&1; then
  echo "FAIL: --todo (untracked) - the done/ destination did not land"
  fail=1
else
  echo "PASS: --todo (untracked) - the done/ destination landed"
fi

# --- AI attribution refusal: a Co-Authored-By: Claude/Anthropic trailer line never lands,
# checked before any repo work so the refusal is cheap and creates no commit ---
r40=$(new_repo); tmp_dirs+=("$r40")
branch=$(git -C "$r40" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r40" rev-parse HEAD)
printf 'f\n' > "$r40/f.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r40" --expect-branch "$branch" --expect-sha "$sha" \
  -m "$(printf 'add f.txt\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')" -- f.txt 2>&1); rc=$?
check "a Co-Authored-By: Claude trailer is refused, naming the matched line (todo 1117)" \
  1 'REFUSED.*AI attribution.*Co-Authored-By: Claude Opus 5\.5' '' "$out" "$rc"
if [ "$(git -C "$r40" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: todo 1117 - an AI-attribution-trailer commit must not have landed"
  fail=1
else
  echo "PASS: todo 1117 - AI-attribution-trailer commit was refused, HEAD untouched"
fi

# --- AI attribution refusal: a HUMAN Co-Authored-By trailer is unaffected ---
r41=$(new_repo); tmp_dirs+=("$r41")
branch=$(git -C "$r41" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r41" rev-parse HEAD)
printf 'f\n' > "$r41/f.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r41" --expect-branch "$branch" --expect-sha "$sha" \
  -m "$(printf 'add f.txt\n\nCo-Authored-By: Jane Doe <jane@x.com>')" -- f.txt 2>&1); rc=$?
check "a human Co-Authored-By trailer still commits (todo 1117)" \
  0 '\[commit\] committed' 'REFUSED' "$out" "$rc"
if [ "$(git -C "$r41" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: todo 1117 - the human-trailer commit did not land"
  fail=1
else
  echo "PASS: todo 1117 - the human-trailer commit landed"
fi

# --- AI attribution refusal: a subject merely mentioning "Claude" in prose is unaffected -
# mc_plugins_tag has many such subjects naming the in-game character ---
r42=$(new_repo); tmp_dirs+=("$r42")
branch=$(git -C "$r42" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r42" rev-parse HEAD)
printf 'f\n' > "$r42/f.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r42" --expect-branch "$branch" --expect-sha "$sha" \
  -m "FIX: Player Claude listener" -- f.txt 2>&1); rc=$?
check "a subject mentioning Claude in prose (not a trailer) still commits (todo 1117)" \
  0 '\[commit\] committed' 'REFUSED' "$out" "$rc"
if [ "$(git -C "$r42" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: todo 1117 - the Player-Claude-subject commit did not land"
  fail=1
else
  echo "PASS: todo 1117 - the Player-Claude-subject commit landed"
fi

# --- AI attribution refusal: a "Generated with [Claude Code]" line is refused too, with or
# without the brackets ---
r43=$(new_repo); tmp_dirs+=("$r43")
branch=$(git -C "$r43" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r43" rev-parse HEAD)
printf 'f\n' > "$r43/f.txt"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r43" --expect-branch "$branch" --expect-sha "$sha" \
  -m "$(printf 'add f.txt\n\nGenerated with [Claude Code]')" -- f.txt 2>&1); rc=$?
check "a Generated with [Claude Code] line is refused, naming the matched line (todo 1117)" \
  1 'REFUSED.*AI attribution.*Generated with \[Claude Code\]' '' "$out" "$rc"
if [ "$(git -C "$r43" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: todo 1117 - a Generated-with-Claude-Code commit must not have landed"
  fail=1
else
  echo "PASS: todo 1117 - Generated-with-Claude-Code commit was refused, HEAD untouched"
fi

# --- directory pathspec coverage: deleting two tracked files under a tracked dir
# and committing with -- <dir> must pass without --force coverage. A new sibling file in the
# SAME nested subdirectory (vendor/scripts/new.mjs) is included deliberately: it is exactly what
# made the old same-directory heuristic fire a false REFUSED in the real incident (a co-located
# add alongside the old heuristic's directory-level dirname match), so this fixture proves the
# new containment check wins over that heuristic rather than merely avoiding triggering it ---
r38=$(new_repo); tmp_dirs+=("$r38")
mkdir -p "$r38/vendor/scripts"
printf 'keep\n' > "$r38/vendor/scripts/keep.mjs"
printf 'one\n' > "$r38/vendor/scripts/one.mjs"
printf 'two\n' > "$r38/vendor/scripts/two.mjs"
git -C "$r38" add vendor/scripts/keep.mjs vendor/scripts/one.mjs vendor/scripts/two.mjs
git -C "$r38" commit -q -m "seed vendor/scripts"
branch=$(git -C "$r38" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r38" rev-parse HEAD)
rm "$r38/vendor/scripts/one.mjs" "$r38/vendor/scripts/two.mjs"
printf 'new\n' > "$r38/vendor/scripts/new.mjs"
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r38" --expect-branch "$branch" --expect-sha "$sha" \
  -m "directory pathspec covers deletions under it, new sibling file too" -- vendor 2>&1); rc=$?
check "a directory pathspec covers deletions nested under it, no coverage refusal (todo 1134)" \
  0 'coverage-check.*clean' 'coverage-check.*REFUSED' "$out" "$rc"
if [ "$(git -C "$r38" rev-parse HEAD)" = "$sha" ]; then
  echo "FAIL: todo 1134 - directory-pathspec deletion commit did not land"
  fail=1
else
  echo "PASS: todo 1134 - directory-pathspec deletion commit landed"
fi
if git -C "$r38" ls-files --error-unmatch -- vendor/scripts/one.mjs vendor/scripts/two.mjs >/dev/null 2>&1; then
  echo "FAIL: todo 1134 - the deleted files under vendor/scripts are still tracked after the commit"
  fail=1
else
  echo "PASS: todo 1134 - the deleted files under vendor/scripts landed as deletions"
fi

# --- directory pathspec coverage regression guard: a staged deletion outside EVERY
# pathspec entry, sharing a directory with a named FILE entry (not a directory entry), must still
# refuse exactly as before - proves the new directory-containment check only short-circuits for
# an actual directory pathspec entry and never swallows the pre-existing same-directory-file
# heuristic ---
r39=$(new_repo); tmp_dirs+=("$r39")
mkdir -p "$r39/mixed"
printf 'target\n' > "$r39/mixed/target.txt"
printf 'other\n' > "$r39/mixed/other.txt"
git -C "$r39" add mixed/target.txt mixed/other.txt
git -C "$r39" commit -q -m "seed mixed/target.txt mixed/other.txt"
branch=$(git -C "$r39" rev-parse --abbrev-ref HEAD)
sha=$(git -C "$r39" rev-parse HEAD)
printf 'target EDITED\n' > "$r39/mixed/target.txt"
git -C "$r39" rm -q mixed/other.txt
out=$(COMMIT_PATHSPEC_SESSION_MARKER_DIR="$solo_marker_dir" "$cp" -C "$r39" --expect-branch "$branch" --expect-sha "$sha" \
  -m "edit target.txt, unrelated staged delete of sibling named only as a FILE entry" -- mixed/target.txt 2>&1); rc=$?
check "a staged deletion outside every pathspec entry, sharing a directory with a named FILE entry, still refuses (todo 1134 regression guard)" \
  1 'coverage-check.*REFUSED.*mixed/other\.txt' '' "$out" "$rc"
if [ "$(git -C "$r39" rev-parse HEAD)" != "$sha" ]; then
  echo "FAIL: todo 1134 regression guard - a refused coverage-check must not have committed anything"
  fail=1
else
  echo "PASS: todo 1134 regression guard - refused coverage-check left HEAD untouched"
fi

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
