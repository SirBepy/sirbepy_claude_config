#!/usr/bin/env bash
# Unpushed-overlap check (todo 474): hunk-level overlap between this commit's pending changes
# and this session's own unpushed history. NOT a prefilter-gate.sh member - a hit is not always
# a block (skills/commit/SKILL.md step 8 defines interactive-ask vs unattended-proceed-and-record;
# that policy stays in SKILL.md, this script only reports).

# Usage: overlap-check.sh [-C|--repo <repo>] <file> [<file> ...]
# Exit 0 clean (no upstream, no candidates, or line-disjoint candidates printed as info only).
# Exit 1 a real hunk-level hit, printed as "<file>:<a>-<end> <short-sha> <subject>".
# Exit 2 could not run (no args, bad/missing repo).
set -uo pipefail

repo=""
if [ "${1:-}" = "-C" ] || [ "${1:-}" = "--repo" ]; then
  repo="${2:-}"
  shift 2
fi
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

if [ $# -eq 0 ]; then
  printf 'ERROR: no files given\n'
  exit 2
fi
if ! git_c rev-parse --show-toplevel >/dev/null 2>&1; then
  printf 'ERROR: %s is not a git repository\n' "${repo:-.}"
  exit 2
fi

# No upstream: nothing to compare against, per SKILL.md step 8.
git_c rev-parse '@{u}' >/dev/null 2>&1 || exit 0

# Full 40-char hashes only, both sides. `git log --format=%h` is 7 chars and default `git
# blame` is 8 with boundary commits prefixed `^` - comparing those two forms is how todo 474
# silently missed real hits twice. `--porcelain` blame emits the full sha with no `^`, so
# comparing full hashes throughout removes the mismatch instead of stripping/padding around it.
mapfile -t candidates < <(git_c log '@{u}..HEAD' --format='%H')
[ "${#candidates[@]}" -eq 0 ] && exit 0

declare -A subject_of
for s in "${candidates[@]}"; do subject_of["$s"]=$(git_c show -s --format='%s' "$s"); done

status=0
for f in "$@"; do
  file_candidates=()
  for s in "${candidates[@]}"; do
    if git_c show --name-only --format= "$s" -- "$f" 2>/dev/null | grep -qxF -- "$f"; then
      file_candidates+=("$s")
    fi
  done
  [ "${#file_candidates[@]}" -eq 0 ] && continue

  if git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    diff_out=$(git_c diff HEAD -- "$f")
  else
    diff_out=$(git_c diff --no-index -- /dev/null "$f" 2>/dev/null)
  fi

  declare -A matched
  while IFS= read -r line; do
    [[ "$line" == '@@ -'* ]] || continue
    # @@ -a[,b] +c[,d] @@ ; b omitted means 1, b=0 is a pure addition and cannot overlap.
    spec=${line#@@ -}; spec=${spec%% +*}
    a=${spec%%,*}
    if [ "$spec" = "$a" ]; then b=1; else b=${spec#*,}; fi
    [ "$b" -eq 0 ] && continue
    end=$((a + b - 1))
    # Dedup: a hunk spanning several lines blamed to the same commit would otherwise repeat
    # the same range/sha line once per source line instead of once per hunk.
    mapfile -t bshas < <(git_c blame --porcelain -L "$a,$end" HEAD -- "$f" 2>/dev/null \
      | grep -oE '^[0-9a-f]{40}' | sort -u)
    for bsha in "${bshas[@]}"; do
      for cs in "${file_candidates[@]}"; do
        if [ "$bsha" = "$cs" ]; then
          short=$(git_c rev-parse --short "$cs")
          printf '%s:%s-%s %s %s\n' "$f" "$a" "$end" "$short" "${subject_of[$cs]}"
          matched["$cs"]=1
          status=1
        fi
      done
    done
  done <<<"$diff_out"

  for cs in "${file_candidates[@]}"; do
    if [ -z "${matched[$cs]:-}" ]; then
      short=$(git_c rev-parse --short "$cs")
      printf '%s: unrelated commit %s, no shared lines\n' "$f" "$short"
    fi
  done
  unset matched
done

exit $status
