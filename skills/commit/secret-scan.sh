#!/usr/bin/env bash
# Secret-scan prefilter: added lines only, mirrors skills/commit/comment-noise.sh's
# shape/exit convention. A pre-existing secret on an unchanged line is not this diff's
# business - it needs its own scrub, not a blocked commit.

# Usage: secret-scan.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        secret-scan.sh --range <base>        range mode (/create-pr drafting step)

# No set -e: expected nonzero exits become a loud stdout ERROR below, never a silent
# abort, which step 5a's "no output means clean" contract would read as passing.
set -uo pipefail

AWK='
/^\+\+\+ b\// {
  f=substr($0,7)
  skip = (f ~ /\.env\.example$/ || f ~ /\.md$/)
  next
}
/^@@/ { match($0, /\+[0-9]+/); ln=substr($0, RSTART+1, RLENGTH-1)+0; next }
/^\+/ && !/^\+\+\+/ {
  l=substr($0,2)
  if (skip) { ln++; next }
  lo=tolower(l)
  if (match(lo, /(password|passwd|secret|token|api[_-]?key|bearer)[a-z0-9_]*[[:space:]]*[:=][[:space:]]*['\''"][^'\''"]{6,}['\''"]/ )) {
    seg=substr(l, RSTART, RLENGTH); loseg=substr(lo, RSTART, RLENGTH)
    if (match(loseg, /['\''"][^'\''"]{6,}['\''"]/ )) {
      val=substr(loseg, RSTART+1, RLENGTH-2)
      if (val !~ /xxx|changeme|your-.*-here|placeholder|example|dummy|redacted|<.*>|^test$|^fake$|^null$|^none$|^undefined$|^password$|^secret$|^string$|^todo$/) {
        printf "%s:%d: %s\n", f, ln, seg
      }
    }
  }
  ln++
  next
}
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk "$AWK" | sort
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
  } | awk "$AWK" | sort
fi
