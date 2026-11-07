#!/usr/bin/env bash
# Self-test for barrier-commit.sh. Runs against a scratch git repo with a FAKE
# commit-pathspec.sh that records its argv and exits with $FAKE_RC; hunk-ranges.sh is the real one.
# Run: bash skills/mega-todos/test_barrier_commit.sh   (exit 0 = all pass)
set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
barrier="$here/barrier-commit.sh"
real_ranges="$here/../commit/hunk-ranges.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

fails=0
ok()   { echo "PASS $1"; }
bad()  { echo "FAIL $1"; fails=$((fails + 1)); }
check() { if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }

repo="$tmp/repo"
mkdir -p "$repo"
git -C "$repo" init -q
git -C "$repo" config user.email t@example.com
git -C "$repo" config user.name t
seq 1 40 >"$repo/a.txt"
echo base >"$repo/b.txt"
git -C "$repo" add a.txt b.txt
git -C "$repo" commit -q -m seed

# Two hunks in a.txt (line 2 and line 38), a modified b.txt, and a brand-new untracked c.txt.
sed -e '2s/.*/two/' -e '38s/.*/thirty-eight/' "$repo/a.txt" >"$tmp/a.new" && cp "$tmp/a.new" "$repo/a.txt"
echo more >>"$repo/b.txt"
echo new >"$repo/c.txt"

# Fake commit-pathspec: one argv entry per line into $FAKE_LOG, refusal text on stdout, status $FAKE_RC.
cat >"$tmp/fake-commit.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$FAKE_LOG"
if [ "${FAKE_RC:-0}" != "0" ]; then echo "[coverage-tests-check] REFUSED (fake)"; fi
exit "${FAKE_RC:-0}"
EOF
export BARRIER_COMMIT_PATHSPEC_SH="$tmp/fake-commit.sh"
export BARRIER_COMMIT_HUNK_RANGES_SH="$real_ranges"
export FAKE_LOG="$tmp/argv.log"

printf 'a.txt\r\nb.txt\r\n\r\nc.txt\r\n' >"$tmp/files.txt"

# --- success path -----------------------------------------------------------------------------
FAKE_RC=0 bash "$barrier" -C "$repo" --expect-branch main --expect-sha abc123 \
  -m "FIX: title" -m "body text" --force coverage-tests --todo pc-1 --files-from "$tmp/files.txt" >"$tmp/out" 2>&1
rc=$?
check "$([ $rc -eq 0 ] && echo 0 || echo 1)" "success exits 0 (got $rc)"

log=$(cat "$FAKE_LOG")
check "$(grep -qx -- '--expect-branch' <<<"$log" && grep -qx 'main' <<<"$log" && grep -qx 'abc123' <<<"$log" && echo 0 || echo 1)" "expect-branch and expect-sha pass through"
check "$(grep -qx 'FIX: title' <<<"$log" && grep -qx 'body text' <<<"$log" && echo 0 || echo 1)" "title and body become -m arguments"
check "$(grep -qx -- '--force' <<<"$log" && grep -qx 'coverage-tests' <<<"$log" && grep -qx -- '--todo' <<<"$log" && grep -qx 'pc-1' <<<"$log" && echo 0 || echo 1)" "--force and --todo pass through"
check "$(grep -qx 'a.txt:2-2,38-38' <<<"$log" && echo 0 || echo 1)" "a.txt gets both of its current hunks as its own range"
check "$(grep -qx 'b.txt:2-2' <<<"$log" && echo 0 || echo 1)" "b.txt gets its appended line as its own range"
check "$(grep -q '^c.txt:' <<<"$log" && echo 1 || echo 0)" "untracked c.txt gets no own-range (commit-pathspec handles new files)"
check "$(grep -qx 'c.txt' <<<"$log" && grep -qx 'a.txt' <<<"$log" && echo 0 || echo 1)" "every listed file reaches the pathspec"
# Compared by byte count: Git Bash's grep drops a CR from its pattern, so grep $'\r' matches every line.
check "$([ "$(tr -d '\r' <"$FAKE_LOG" | wc -c)" = "$(wc -c <"$FAKE_LOG")" ] && echo 0 || echo 1)" "CRLF from the files-from list never reaches commit-pathspec.sh"
check "$(grep -qx -- '--' <<<"$log" && echo 0 || echo 1)" "files follow a -- separator"

# --- a refusal must read as failure -----------------------------------------------------------
FAKE_RC=1 bash "$barrier" -C "$repo" -m "FIX: t" -- a.txt >"$tmp/out" 2>&1
rc=$?
check "$([ $rc -eq 1 ] && echo 0 || echo 1)" "a refused commit exits non-zero (got $rc)"
check "$(grep -q 'REFUSED' "$tmp/out" && echo 0 || echo 1)" "the refusal text reaches the caller"
FAKE_RC=3 bash "$barrier" -C "$repo" -m "FIX: t" -- a.txt >/dev/null 2>&1
rc=$?
check "$([ $rc -eq 3 ] && echo 0 || echo 1)" "the child's own exit code is propagated (got $rc)"

# --- default expect values come from the repo ----------------------------------------------------
FAKE_RC=0 bash "$barrier" -C "$repo" -m "FIX: t" -- a.txt >/dev/null 2>&1
head_sha=$(git -C "$repo" rev-parse HEAD)
check "$(grep -qx "$head_sha" "$FAKE_LOG" && echo 0 || echo 1)" "omitted --expect-sha is read from the repo"

# --- opt-out and argument errors ---------------------------------------------------------------------
FAKE_RC=0 bash "$barrier" -C "$repo" --no-own-ranges -m "FIX: t" -- a.txt >/dev/null 2>&1
check "$(grep -q -- '--own-range' "$FAKE_LOG" && echo 1 || echo 0)" "--no-own-ranges declares nothing"

bash "$barrier" -C "$repo" -- a.txt >/dev/null 2>&1
check "$([ $? -eq 2 ] && echo 0 || echo 1)" "missing -m exits 2"
bash "$barrier" -C "$repo" -m "FIX: t" >/dev/null 2>&1
check "$([ $? -eq 2 ] && echo 0 || echo 1)" "no files exits 2"
bash "$barrier" -C "$repo" -m "FIX: t" --files-from "$tmp/nope.txt" >/dev/null 2>&1
check "$([ $? -eq 2 ] && echo 0 || echo 1)" "a missing --files-from file exits 2"
bash "$barrier" -C "$repo" --bogus -m "FIX: t" -- a.txt >/dev/null 2>&1
check "$([ $? -eq 2 ] && echo 0 || echo 1)" "an unknown flag exits 2"

if [ "$fails" -gt 0 ]; then echo "FAIL: $fails check(s) failed"; exit 1; fi
echo "OK: all checks passed"
