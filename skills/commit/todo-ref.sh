#!/usr/bin/env bash
# Todo-number-in-comment prefilter: flags an added code comment that cites a backlog todo id by
# number (a marker, whitespace, then "todo" plus an id - an optional space or dash, an optional
# "#", then one to four digits) so a builder dispatch's prose instruction isn't the only thing
# stopping it from landing in source. A bare marker/word with no trailing digits is NOT flagged -
# only the numbered-id shape is. Fix-and-continue treatment like comment-tense.sh, not a STOP
# like secret-scan.sh. This comment block deliberately never spells out a real example in the
# flagged shape (marker-whitespace-"todo"-id), or the check would flag its own source.

# Usage: todo-ref.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        todo-ref.sh --range <base>        range mode (/create-pr, branch diff)
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$script_dir/_prefilter-lib.sh" || { printf 'ERROR: missing prefilter lib: %s/_prefilter-lib.sh\n' "$script_dir"; exit 1; }

# Anchored to the start of the comment (mirrors comment-tense.sh's own anchoring) so a `*` or
# `--` used as an operator mid-line never matches: the line itself must OPEN with a marker then
# whitespace. gawk's `\y` is a word-boundary (its `\b` means backspace, not a boundary), which is
# what keeps an unrelated word ending in digits, or a URL path segment, from matching while still
# catching the real shape (word, then an optional space-or-dash, an optional "#", then digits),
# case-insensitively.
AWK='
BEGIN { IGNORECASE = 1 }
/^\+\+\+ b\// { f=substr($0,7); next }
/^\+/ && !/^\+\+\+/ {
  if (f ~ /\.(md|mdx)$/) next
  if (f ~ /(^|\/)\.claude\/todos\//) next
  l=substr($0,2)
  if (l ~ /^[[:space:]]*(\/\/|#|\/\*|\*|--)[[:space:]].*\ytodo[ -]?#?[0-9]{1,4}\y/) {
    printf "%s: %s\n", f, l
  }
  next
}
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd; absent, git_c is a passthrough and behaviour is unchanged.
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
