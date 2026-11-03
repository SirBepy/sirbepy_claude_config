#!/usr/bin/env bash
# Prints, per file, the `--own-range` argument for its current hunks vs HEAD plus each hunk's first
# changed line, so a caller can read them and pass to commit-pathspec.sh only the hunks it owns.
# Print only, never claims anything: whether every hunk is this session's own is a judgement the
# caller makes, and a whole-file claim is exactly what the own-range check exists to catch.
#
#   bash hunk-ranges.sh <file>...
#
# The range arithmetic mirrors derive_own_ranges in commit-pathspec.sh (that function sits in a
# script that runs its whole pipeline on source, so it is not callable from here): `@@ -a,b +c,d @@`
# becomes c-(c+d-1), and a pure-deletion hunk (+c,0) contributes no new-file lines so it is omitted.
set -uo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: hunk-ranges.sh <file>..." >&2
  exit 2
fi

for f in "$@"; do
  diff_out=$(git diff -U0 HEAD -- "$f" 2>/dev/null)
  ranges=""
  detail=""
  header=""
  first_line=""
  while IFS= read -r line; do
    if [[ "$line" == '@@ -'* ]]; then
      if [ -n "$header" ] && [ -n "$first_line" ]; then
        detail+="  $header"$'\n'"    $first_line"$'\n'
      fi
      header="$line"
      first_line=""
      rest=${line#*+}
      newspec=${rest%% @@*}
      c=${newspec%%,*}
      if [ "$newspec" = "$c" ]; then d=1; else d=${newspec#*,}; fi
      if [ "$d" -ne 0 ]; then ranges+="${c}-$((c + d - 1)),"; fi
      continue
    fi
    if [ -n "$header" ] && [ -z "$first_line" ] && { [[ "$line" == '+'* ]] || [[ "$line" == '-'* ]]; }; then
      first_line="$line"
    fi
  done <<<"$diff_out"
  if [ -n "$header" ] && [ -n "$first_line" ]; then
    detail+="  $header"$'\n'"    $first_line"$'\n'
  fi

  if [ -z "$header" ]; then
    echo "# $f: no hunks vs HEAD (unchanged, untracked, or not in this repo)"
    continue
  fi
  if [ -z "$ranges" ]; then
    echo "# $f: only pure-deletion hunks, no new-file lines to claim"
  else
    echo "--own-range $f:${ranges%,}"
  fi
  printf '%s' "$detail"
done
