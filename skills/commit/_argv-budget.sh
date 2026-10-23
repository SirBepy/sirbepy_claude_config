#!/usr/bin/env bash
# The command-line length budget and its over-budget test, dot-sourced by _prefilter-lib.sh and
# commit-pathspec.sh so both split a path list at the same point. Kept apart from _prefilter-lib.sh
# because that file also defines a global `repo` and its own git_c, which commit-pathspec.sh must
# not inherit (it has a different git_c and uses repo_root).

# Windows caps one command line near 32K characters, and a generated-asset commit names more
# paths than that. Everything that hands a whole path list to an external command either splits it
# at this many characters or moves it through a file; PREFILTER_ARGV_BUDGET lets a test force the
# split with a handful of paths.
PREFILTER_ARGV_BUDGET="${PREFILTER_ARGV_BUDGET:-12000}"

# True when "$@" would not fit in one external command's argv budget (each arg counts its length
# plus one for the separator).
paths_over_budget() {
  local p total=0
  for p in "$@"; do
    total=$((total + ${#p} + 1))
    [ "$total" -gt "$PREFILTER_ARGV_BUDGET" ] && return 0
  done
  return 1
}
