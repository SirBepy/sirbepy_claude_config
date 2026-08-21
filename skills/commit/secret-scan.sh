#!/usr/bin/env bash
# Secret-scan prefilter: added lines only, mirrors skills/commit/comment-noise.sh's
# shape/exit convention. A pre-existing secret on an unchanged line is not this diff's
# business - it needs its own scrub, not a blocked commit.
#
# Patterns come from hooks/secret-patterns.txt (todo 420), shared with
# hooks/secret-write-guard.py so the two can never drift.

# Usage: secret-scan.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        secret-scan.sh --range <base>        range mode (/create-pr drafting step)

# No set -e: expected nonzero exits become a loud stdout ERROR below, never a silent
# abort, which step 5a's "no output means clean" contract would read as passing.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
patfile="$script_dir/../../hooks/secret-patterns.txt"

if [ ! -f "$patfile" ]; then
  printf 'ERROR: secret pattern file missing: %s\n' "$patfile"
  exit 1
fi

AWK='
BEGIN {
  if ((getline probe < PATFILE) < 0) {
    print "ERROR: cannot read secret pattern file: " PATFILE
    exit 1
  }
  close(PATFILE)
  npat = 0; nallow = 0
  while ((getline row < PATFILE) > 0) {
    if (row ~ /^#/ || row ~ /^[ \t]*$/) continue
    n = split(row, col, "\t")
    if (n != 3) continue
    if (col[1] == "pattern") { npat++; pname[npat] = col[2]; prex[npat] = col[3] }
    else if (col[1] == "allow") { nallow++; arex[nallow] = col[3] }
  }
  close(PATFILE)
  if (npat == 0) {
    print "ERROR: zero pattern rows loaded from " PATFILE
    exit 1
  }
}
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
  for (i=1; i<=npat; i++) {
    if (!match(lo, prex[i])) continue
    seg=substr(l, RSTART, RLENGTH)
    if (pname[i] == "generic_assignment") {
      loseg=substr(lo, RSTART, RLENGTH)
      if (match(loseg, /['\''"][^'\''"\t ,)]{6,}['\''"]/)) {
        val=substr(loseg, RSTART+1, RLENGTH-2)
        allowed=0
        for (j=1; j<=nallow; j++) if (match(val, arex[j])) { allowed=1; break }
        if (allowed) continue
      }
    }
    printf "%s:%d: %s\n", f, ln, seg
    break
  }
  ln++
  next
}
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk -v PATFILE="$patfile" "$AWK" | sort
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
  } | awk -v PATFILE="$patfile" "$AWK" | sort
fi
