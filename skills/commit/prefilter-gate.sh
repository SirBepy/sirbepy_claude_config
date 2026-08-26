#!/usr/bin/env bash
# Prefilter gate: runs comment-noise.sh, comment-tense.sh, em-dash.sh, secret-scan.sh; exits non-zero if any
# prints or errors, so `prefilter-gate.sh <files> && git commit ...` structurally blocks a
# flagged diff. Wraps the three scripts unchanged - they still work standalone. Todo 356.

# Usage: prefilter-gate.sh [-C <repo>|--repo <repo>] <file> [<file> ...]   working-tree mode
#        prefilter-gate.sh --range <base>                                  range mode, forwarded as-is
# Exit 0 = clean, 1 = a prefilter flagged something, 2 = could not run (bad path, no repo found).
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
status=0
repo=""

if [ "${1:-}" = "-C" ] || [ "${1:-}" = "--repo" ]; then
  repo="${2:-}"
  shift 2
  if ! git -C "$repo" rev-parse --show-toplevel >/dev/null 2>&1; then
    printf 'ERROR: %s is not a git repository\n' "$repo"
    exit 2
  fi
elif [ "${1:-}" != "--range" ] && [ $# -gt 0 ]; then
  # A path inside a submodule resolves to the SUBMODULE's own root, not the parent's, so
  # keying off argv[1] alone (as 447 did) leaves any other group's paths silently unresolved
  # (todo 412). Group every path by its own resolved repo instead.
  cwd_repo=$(git rev-parse --show-toplevel 2>/dev/null)
  declare -A group_paths
  for a in "$@"; do
    arg_repo=$(git -C "$(dirname -- "$a")" rev-parse --show-toplevel 2>/dev/null)
    if [ -z "$arg_repo" ]; then
      printf 'ERROR: could not find a git repository for %s\n' "$a"
      exit 2
    fi
    if [ "$arg_repo" = "$cwd_repo" ]; then
      rel="$a"
    else
      # `git -C <repo> diff` resolves pathspecs against the NEW cwd, not the caller's, so a
      # parent-relative path silently misses once forwarded - rebuild it relative to its own root.
      prefix=$(git -C "$(dirname -- "$a")" rev-parse --show-prefix 2>/dev/null)
      rel="${prefix}$(basename -- "$a")"
    fi
    group_paths["$arg_repo"]+="$rel"$'\n'
  done

  for repo_key in "${!group_paths[@]}"; do
    readarray -t rels <<<"${group_paths[$repo_key]}"
    paths=()
    for r in "${rels[@]}"; do [ -n "$r" ] && paths+=("$r"); done
    for script in comment-noise.sh comment-tense.sh em-dash.sh secret-scan.sh; do
      if [ "$repo_key" = "$cwd_repo" ]; then
        out=$(bash "$dir/$script" "${paths[@]}")
      else
        out=$(bash "$dir/$script" --repo "$repo_key" "${paths[@]}")
      fi
      rc=$?
      if [ -n "$out" ] || [ "$rc" -ne 0 ]; then
        # cwd's own repo prints the plain header so this stays byte-identical to before todo
        # 412; a forwarded repo (submodule or otherwise) names itself in the header.
        if [ "$repo_key" = "$cwd_repo" ]; then
          printf '=== %s ===\n%s\n' "$script" "$out"
        else
          printf '=== %s (%s) ===\n%s\n' "$script" "$repo_key" "$out"
        fi
        status=1
      fi
    done
  done
  exit $status
fi

for script in comment-noise.sh comment-tense.sh em-dash.sh secret-scan.sh; do
  if [ -n "$repo" ]; then
    out=$(bash "$dir/$script" --repo "$repo" "$@")
  else
    out=$(bash "$dir/$script" "$@")
  fi
  rc=$?
  if [ -n "$out" ] || [ "$rc" -ne 0 ]; then
    printf '=== %s ===\n%s\n' "$script" "$out"
    status=1
  fi
done

exit $status
