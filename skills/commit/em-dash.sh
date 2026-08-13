#!/usr/bin/env bash
# Em-dash prefilter: added lines only, mirrors skills/commit/comment-noise.sh's shape/exit
# convention. A pre-existing em dash on an unchanged line is not this diff's business.

# Usage: em-dash.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        em-dash.sh --range <base>        range mode (delegation-doctrine builder prefilter)
set -euo pipefail

# Built from raw UTF-8 bytes, never the literal character, so this file itself never trips its own
# check or any other em-dash scan of this repo.
ED=$(printf '\xe2\x80\x94')

AWK='
/^\+\+\+ b\// { f=substr($0,7); next }
/^@@/ { match($0, /\+[0-9]+/); ln=substr($0, RSTART+1, RLENGTH-1)+0; next }
/^\+/ && !/^\+\+\+/ { l=substr($0,2); if (index(l, ED) > 0) printf "%s:%d\n", f, ln; ln++; next }
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  git diff "$2" | awk -v ED="$ED" "$AWK" | sort
else
  {
    git diff HEAD -- "$@"
    git status --porcelain -- "$@" | awk '$1=="??"{print substr($0,4)}' | while IFS= read -r f; do
      # --no-index exits 1 whenever the files differ, which is always here; pipefail would abort.
      git diff --no-index -- /dev/null "$f" || true
    done
  } | awk -v ED="$ED" "$AWK" | sort
fi
