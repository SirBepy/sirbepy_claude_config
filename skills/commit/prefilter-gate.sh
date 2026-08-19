#!/usr/bin/env bash
# Prefilter gate: runs comment-noise.sh, em-dash.sh, secret-scan.sh; exits non-zero if any
# prints or errors, so `prefilter-gate.sh <files> && git commit ...` structurally blocks a
# flagged diff. Wraps the three scripts unchanged - they still work standalone. Todo 356.

# Usage: prefilter-gate.sh <file> [<file> ...]   working-tree mode (/commit step 5a/8)
#        prefilter-gate.sh --range <base>        range mode, forwarded as-is to each script
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
status=0

for script in comment-noise.sh em-dash.sh secret-scan.sh; do
  out=$(bash "$dir/$script" "$@")
  rc=$?
  if [ -n "$out" ] || [ "$rc" -ne 0 ]; then
    printf '=== %s ===\n%s\n' "$script" "$out"
    status=1
  fi
done

exit $status
