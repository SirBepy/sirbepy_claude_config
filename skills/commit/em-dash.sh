#!/usr/bin/env bash
# Em-dash prefilter: added lines only, mirrors skills/commit/comment-noise.sh's shape/exit
# convention. A pre-existing em dash on an unchanged line is not this diff's business.

# Usage: em-dash.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        em-dash.sh --range <base>        range mode (delegation-doctrine builder prefilter)

# No set -e: expected nonzero exits become a loud stdout ERROR below, never a silent
# abort, which step 5a's "no output means clean" contract would read as passing.
set -uo pipefail

# Raw bytes, never the literal character, so this file never trips its own check.
ED=$(printf '\xe2\x80\x94')

AWK='
/^\+\+\+ b\// { f=substr($0,7); next }
/^@@/ { match($0, /\+[0-9]+/); ln=substr($0, RSTART+1, RLENGTH-1)+0; next }
/^\+/ && !/^\+\+\+/ { l=substr($0,2); if (index(l, ED) > 0) printf "%s:%d\n", f, ln; ln++; next }
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk -v ED="$ED" "$AWK" | sort
else
  {
    git diff HEAD -- "$@"
    # -z/NUL-separated: git status quotes space-containing names, which broke the downstream
    # git diff --no-index call; ls-files -z sidesteps quoting entirely.
    git ls-files --others --exclude-standard -z -- "$@" | while IFS= read -r -d '' f; do
      out=$(git diff --no-index -- /dev/null "$f" 2>&1); rc=$?
      if [ "$rc" -gt 1 ]; then
        printf 'ERROR: could not inspect untracked file %s (git diff --no-index exit %d): %s\n' "$f" "$rc" "$out"
      else
        printf '%s\n' "$out"
      fi
    done
  } | awk -v ED="$ED" "$AWK" | sort
fi
