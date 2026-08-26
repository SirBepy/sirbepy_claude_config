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
  # Resolve the target repo from the first path argument instead of assuming cwd, so an
  # absolute path into a different repo fails with one line instead of raw git fatals (todo 447).
  arg_repo=$(git -C "$(dirname -- "$1")" rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$arg_repo" ]; then
    printf 'ERROR: could not find a git repository for %s\n' "$1"
    exit 2
  fi
  cwd_repo=$(git rev-parse --show-toplevel 2>/dev/null)
  [ "$arg_repo" != "$cwd_repo" ] && repo="$arg_repo"
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
