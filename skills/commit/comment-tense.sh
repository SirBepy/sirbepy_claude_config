#!/usr/bin/env bash
# Timeless-Present prefilter: flags comments that narrate the change instead of stating the
# invariant. Rule, measured false-positive rate, and the rejected patterns are all in
# skills/commit/comment-noise.md. Todo 429.

# Usage: comment-tense.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        comment-tense.sh --range <base>        range mode (/create-pr, branch diff)
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$script_dir/_prefilter-lib.sh" || { printf 'ERROR: missing prefilter lib: %s/_prefilter-lib.sh\n' "$script_dir"; exit 1; }

AWK='
/^\+\+\+ b\// { f=substr($0,7); incomment=0; next }
/^\+/ && !/^\+\+\+/ {
  if (f ~ /\.(md|mdx)$/) next
  l=substr($0,2)
  if (l !~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { incomment=0; next }
  # strip the comment marker so "first word" means first word of the prose
  body=l
  sub(/^[[:space:]]*(\/\/+|\/\*+|\*+|#+|--+|<!--)[[:space:]]*/, "", body)
  t=tolower(body)
  # A leading change verb only narrates when it OPENS a block; on a wrapped continuation the
  # same word is mid-sentence, which was the one false-positive class found on the real tree.
  if (!incomment && t ~ /^(added|removed|renamed|replaced|refactored|migrated|bumped)[[:space:]]/) {
    printf "%s: %s\n", f, body
  } else if (t ~ /(we decided to|unlike the old|as of this (change|commit|pr|refactor|fix)|todo from the)/) {
    printf "%s: %s\n", f, body
  }
  incomment=1
  next
}
{ incomment=0 }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  parse_repo_arg "$@"
  set -- "${PREFILTER_ARGS[@]}"
  {
    git_c diff HEAD -- "$@"
    git_c ls-files --others --exclude-standard -z -- "$@" | while IFS= read -r -d '' f; do
      out=$(git_c diff --no-index -- /dev/null "$f" 2>&1); rc=$?
      if [ "$rc" -gt 1 ]; then
        printf 'ERROR: could not inspect untracked file %s (git diff --no-index exit %d): %s\n' "$f" "$rc" "$out"
      else
        printf '%s\n' "$out"
      fi
    done
  } | awk "$AWK" | sort
fi
