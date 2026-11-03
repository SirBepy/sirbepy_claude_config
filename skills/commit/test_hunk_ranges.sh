#!/usr/bin/env bash
# Fixture suite for hunk-ranges.sh. Invoke directly:
#   bash skills/commit/test_hunk_ranges.sh
# Discovered by ci/run_all.py's skills/commit/test_*.sh glob.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
hr="$script_dir/hunk-ranges.sh"

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

check() {
  local name="$1" want="$2" got="$3"
  if [ "$want" = "$got" ]; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"
    echo "  want: $want"
    echo "  got:  $got"
    fail=1
  fi
}

new_repo() {
  local d
  d=$(mktemp -d)
  tmp_dirs+=("$d")
  git -C "$d" init -q
  git -C "$d" config user.email t@example.com
  git -C "$d" config user.name t
  git -C "$d" config core.autocrlf false
  printf '%s\n' "$d"
}

# Two separate hunks: line 3 edited, then 2 lines appended after line 20.
repo=$(new_repo)
for i in $(seq 1 20); do echo "line $i"; done >"$repo/f.txt"
git -C "$repo" add f.txt
git -C "$repo" commit -q -m init
sed -i 's/^line 3$/line 3 changed/' "$repo/f.txt"
printf 'extra a\nextra b\n' >>"$repo/f.txt"

out=$(cd "$repo" && bash "$hr" f.txt)
check "two hunks print exact a-b,c-d" "--own-range f.txt:3-3,21-22" "$(printf '%s\n' "$out" | grep '^--own-range')"
check "first changed line of hunk 1 is shown" "1" "$(printf '%s\n' "$out" | grep -c '^    -line 3$')"
check "first changed line of hunk 2 is shown" "1" "$(printf '%s\n' "$out" | grep -c '^    +extra a$')"

# A pure-deletion hunk (+c,0) is omitted from the range, same as commit-pathspec.sh.
repo=$(new_repo)
for i in $(seq 1 20); do echo "line $i"; done >"$repo/g.txt"
git -C "$repo" add g.txt
git -C "$repo" commit -q -m init
sed -i '5d' "$repo/g.txt"
sed -i 's/^line 15$/line 15 changed/' "$repo/g.txt"
out=$(cd "$repo" && bash "$hr" g.txt)
check "pure deletion hunk omitted" "--own-range g.txt:14-14" "$(printf '%s\n' "$out" | grep '^--own-range')"

# Several files: one --own-range line each; an unchanged file prints no --own-range line.
repo=$(new_repo)
printf 'a\nb\nc\n' >"$repo/a.txt"
printf 'x\ny\nz\n' >"$repo/b.txt"
git -C "$repo" add a.txt b.txt
git -C "$repo" commit -q -m init
printf 'a\nB\nc\n' >"$repo/a.txt"
out=$(cd "$repo" && bash "$hr" a.txt b.txt)
check "changed file prints range" "--own-range a.txt:2-2" "$(printf '%s\n' "$out" | grep '^--own-range')"
check "unchanged file noted, not claimed" "1" "$(printf '%s\n' "$out" | grep -c 'b.txt: no hunks')"

# No arguments is a usage error.
bash "$hr" >/dev/null 2>&1
check "no args exits 2" "2" "$?"

exit $fail
