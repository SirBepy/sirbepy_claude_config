#!/usr/bin/env bash
# Comment-noise prefilter; the cap itself is defined in skills/commit/comment-noise.md.
# On disk rather than markdown-embedded: skill-argument substitution rewrites a bare $0 in a
# skill body, which clobbered awk's $0 ("whole current line") every time this was pasted inline.

# Usage: comment-noise.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        comment-noise.sh --range <base>        range mode (/create-pr step 2, branch diff)
# No set -e: expected nonzero exits (git diff --no-index differs, bad --range sha) are handled
# explicitly below and turned into a loud stdout ERROR line, never a silent abort that reads as
# "no output means clean" per step 5a's contract.
set -uo pipefail

AWK='
/^\+\+\+ b\// { f=substr($0,7); run=0; next }
/^\+/ && !/^\+\+\+/ {
  # Markdown/mdx "#" is a heading, never a comment - the cap is a code rule (todo 340).
  if (f ~ /\.(md|mdx)$/) next
  l=substr($0,2); add[f]++
  if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
  next
}
{ run=0 }
END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }
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
