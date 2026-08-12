#!/usr/bin/env bash
# Comment-noise prefilter; the cap itself is defined in skills/commit/comment-noise.md.
# On disk rather than markdown-embedded: skill-argument substitution rewrites a bare $0 in a
# skill body, which clobbered awk's $0 ("whole current line") every time this was pasted inline.

# Usage: comment-noise.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        comment-noise.sh --range <base>        range mode (/create-pr step 2, branch diff)
set -euo pipefail

AWK='
/^\+\+\+ b\// { f=substr($0,7); run=0; next }
/^\+/ && !/^\+\+\+/ {
  l=substr($0,2); add[f]++
  if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
  next
}
{ run=0 }
END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }
'

if [ "${1:-}" = "--range" ]; then
  git diff "$2" | awk "$AWK" | sort
else
  {
    git diff HEAD -- "$@"
    git status --porcelain -- "$@" | awk '$1=="??"{print substr($0,4)}' | while IFS= read -r f; do
      # --no-index exits 1 whenever the files differ, which is always here; pipefail would abort.
      git diff --no-index -- /dev/null "$f" || true
    done
  } | awk "$AWK" | sort
fi
