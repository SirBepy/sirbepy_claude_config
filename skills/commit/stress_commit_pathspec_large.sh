#!/usr/bin/env bash
# Large-commit scenario for commit-pathspec.sh: ~1000 new files under one directory plus 2 edited
# text files, committed through a directory pathspec. Kept out of the test_*.sh glob that
# ci/run_all.py runs on every push because it takes minutes; a dev runs it by hand:
#   bash skills/commit/stress_commit_pathspec_large.sh [file-count]      (default 1000)
# Env: CP=<path to a commit-pathspec.sh> overrides the script under test; SHAPES="tracked-dir"
# runs one shape; LIMIT_SECS (default 120) is the per-shape time budget; MARKERS=2 runs it as a
# shared checkout.
#
# Two directory shapes, because they take different code paths in commit-pathspec.sh:
#   tracked-dir   the directory already holds a tracked file, so the script expands it into one
#                 entry per changed file (the shape that put ~970 paths into argv, mc_plugins_tag
#                 2026-10-08).
#   untracked-dir the directory is wholly new, so the script passes the bare directory through.
# Windows' ~32K command-line limit is what broke the first shape: every git/bash call handed the
# whole expanded list as argv.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
cp="${CP:-$script_dir/commit-pathspec.sh}"
n="${1:-1000}"
limit_secs="${LIMIT_SECS:-120}"

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

marker_dir=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$marker_dir")
printf 'x' > "$marker_dir/00000001-0000-4000-8000-000000000000"
# MARKERS=2 simulates a checkout shared with a peer session, which takes the multi-session branch.
[ "${MARKERS:-1}" = 2 ] && printf 'x' > "$marker_dir/00000002-0000-4000-8000-000000000000"
export COMMIT_PATHSPEC_SESSION_MARKER_DIR="$marker_dir"

run_shape() {
  local shape="$1" d i dirname out rc start elapsed branch sha new_head committed
  d=$(mktemp -d) || { echo "FAIL: mktemp -d"; fail=1; return; }
  tmp_dirs+=("$d")
  git -C "$d" init -q
  git -C "$d" config user.email "test@example.com"
  git -C "$d" config user.name "test"
  git -C "$d" config core.autocrlf false
  printf 'one\ntwo\n' > "$d/a.txt"
  printf 'one\ntwo\n' > "$d/b.txt"
  # The incident's real asset path (~68 characters), so the expanded list outgrows one command line.
  tracked_dir=server/resourcepacks/claudesmp-items/assets/claudesmp/textures/item
  fresh_dir=server/resourcepacks/claudesmp-items/assets/claudesmp/models/item
  mkdir -p "$d/$tracked_dir"
  printf 'seed\n' > "$d/$tracked_dir/seed.txt"
  git -C "$d" add -A
  git -C "$d" commit -q -m seed

  dirname=$tracked_dir
  [ "$shape" = "untracked-dir" ] && dirname=$fresh_dir
  mkdir -p "$d/$dirname"
  i=1
  while [ "$i" -le "$n" ]; do
    # Every fourth file is a PNG-headed binary so the binary skip path runs at volume.
    if [ $((i % 4)) -eq 0 ]; then
      printf '\x89PNG\r\n\x1a\n\0\0\0\rIHDR%05d' "$i" > "$d/$dirname/item_number_$(printf '%05d' "$i").png"
    else
      printf '{"id": %d}\n' "$i" > "$d/$dirname/item_number_$(printf '%05d' "$i").json"
    fi
    i=$((i + 1))
  done
  printf 'one\ntwo EDITED\n' > "$d/a.txt"
  printf 'one EDITED\ntwo\n' > "$d/b.txt"

  branch=$(git -C "$d" rev-parse --abbrev-ref HEAD)
  sha=$(git -C "$d" rev-parse HEAD)
  start=$SECONDS
  # A shared checkout refuses an auto-derived range on a file that already exists at HEAD, so the
  # two edited files declare theirs.
  own_args=()
  [ "${MARKERS:-1}" = 2 ] && own_args=(--own-range a.txt:1-2 --own-range b.txt:1-2)
  out=$("$cp" -C "$d" --expect-branch "$branch" --expect-sha "$sha" "${own_args[@]}" -m "large generated-asset commit" -- "$dirname" a.txt b.txt 2>&1); rc=$?
  elapsed=$((SECONDS - start))
  new_head=$(git -C "$d" rev-parse HEAD)
  committed=$(git -C "$d" ls-tree -r --name-only HEAD -- "$dirname" | wc -l | tr -d ' ')
  echo "[$shape] $n files, exit $rc, ${elapsed}s, HEAD moved: $([ "$new_head" != "$sha" ] && echo yes || echo no), files under $dirname/ in HEAD: $committed"

  if printf '%s' "$out" | grep -q 'Argument list too long'; then
    echo "FAIL: [$shape] 'Argument list too long' in output"; fail=1
  fi
  if [ "$rc" -ne 0 ] || ! printf '%s' "$out" | grep -q '^\[commit\] committed'; then
    echo "FAIL: [$shape] exit $rc, no '[commit] committed'. Tail of output:"
    printf '%s\n' "$out" | tail -n 15
    fail=1
  fi
  # Tracked-dir shape: seed.txt is already there, so n new files make n + 1.
  want=$n; [ "$shape" = "tracked-dir" ] && want=$((n + 1))
  if [ "$committed" != "$want" ]; then
    echo "FAIL: [$shape] $committed files under $dirname/ in HEAD, want $want"; fail=1
  fi
  if [ -n "$(git -C "$d" status --porcelain)" ]; then
    echo "FAIL: [$shape] working tree not clean after the commit:"
    git -C "$d" status --porcelain | head -n 5
    fail=1
  fi
  if [ "$elapsed" -gt "$limit_secs" ]; then
    echo "FAIL: [$shape] took ${elapsed}s, limit ${limit_secs}s"; fail=1
  fi
}

for shape in ${SHAPES:-tracked-dir untracked-dir}; do run_shape "$shape"; done

if [ "$fail" -eq 0 ]; then echo "ALL PASS"; else echo "SOME FAILED"; fi
exit "$fail"
