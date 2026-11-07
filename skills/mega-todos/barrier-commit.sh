#!/usr/bin/env bash
# One call = one /mega-todos barrier commit (COMMIT_MODE=barrier). Declares each pathspec file's
# current hunks as this session's own, then runs commit-pathspec.sh and EXITS WITH ITS STATUS, so
# a refused commit (overlap, coverage, a live-session marker count) can never read as success.
#
#   bash barrier-commit.sh [-C <repo>] [--expect-branch <b>] [--expect-sha <s>] [--force <check>]...
#       [--todo <id>]... [--no-own-ranges] -m <title> [-m <body>]...
#       (--files-from <file> | -- <file>...)
#
# --files-from reads one path per line (archive-batch.ps1 -PathspecFile writes that file); CR and
# blank lines are stripped, because Python and PowerShell on Windows both write CRLF and a path
# with a trailing CR reads as "not on disk" (2026-11-03 run, 45 commits).
#
# Own ranges: with 2+ live session markers (builder subagents leave them behind) commit-pathspec.sh
# refuses to trust its own auto-derived ranges ("UNVERIFIED, refusing"). In barrier mode the main
# thread verified a clean tree in Step A and the builders never touched git, so every current hunk
# of the lane's files IS this run's; hunk-ranges.sh prints exactly those as --own-range flags. Pass
# --no-own-ranges when a peer may share one of the files. A file with no hunks vs HEAD (untracked,
# deleted) gets no flag: commit-pathspec.sh handles both shapes itself.
#
# --force and --todo pass straight through (e.g. --force coverage-tests for a doc-only change);
# the branch guard and prefilter gate stay non-overridable there. When --expect-branch/--expect-sha
# are omitted they are read from the repo now, which is only right if nothing moved HEAD since the
# barrier began, so a multi-commit barrier should pass the values it recorded.
set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
commit_sh=${BARRIER_COMMIT_PATHSPEC_SH:-"$here/../commit/commit-pathspec.sh"}
ranges_sh=${BARRIER_COMMIT_HUNK_RANGES_SH:-"$here/../commit/hunk-ranges.sh"}

usage() {
  echo "usage: barrier-commit.sh [-C repo] [--expect-branch b] [--expect-sha s] [--force check]... [--todo id]... [--no-own-ranges] -m title [-m body]... (--files-from file | -- file...)" >&2
}

repo=.
expect_branch=""
expect_sha=""
own_ranges=1
files_from=""
messages=()
pass=()
files=()

while [ $# -gt 0 ]; do
  # A value-taking flag as the last argument would make `shift 2` fail without consuming anything
  # and spin this loop forever, so a truncated command line must exit 2 instead.
  case "$1" in
    -C|--repo|--expect-branch|--expect-sha|-m|--force|--todo|--files-from)
      if [ $# -lt 2 ]; then echo "ERROR: $1 needs a value" >&2; usage; exit 2; fi ;;
  esac
  case "$1" in
    -C|--repo) repo="${2:-}"; shift 2 ;;
    --expect-branch) expect_branch="${2:-}"; shift 2 ;;
    --expect-sha) expect_sha="${2:-}"; shift 2 ;;
    -m) messages+=("${2:-}"); shift 2 ;;
    --force|--todo) pass+=("$1" "${2:-}"); shift 2 ;;
    --no-own-ranges) own_ranges=0; shift ;;
    --files-from) files_from="${2:-}"; shift 2 ;;
    --) shift; files+=("$@"); break ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [ "${#messages[@]}" -eq 0 ] || [ -z "${messages[0]}" ]; then
  echo "ERROR: -m <title> is required" >&2; usage; exit 2
fi
if [ -n "$files_from" ]; then
  if [ ! -f "$files_from" ]; then
    echo "ERROR: --files-from $files_from does not exist" >&2; exit 2
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line//$'\r'/}
    [ -n "$line" ] && files+=("$line")
  done <"$files_from"
fi
if [ "${#files[@]}" -eq 0 ]; then
  echo "ERROR: no files: pass -- <file>... or --files-from <file>" >&2; usage; exit 2
fi
for f in "$commit_sh" "$ranges_sh"; do
  if [ ! -f "$f" ]; then echo "ERROR: helper script not found: $f" >&2; exit 2; fi
done
if ! cd "$repo" 2>/dev/null; then echo "ERROR: cannot enter repo: $repo" >&2; exit 2; fi
repo=$(pwd)

[ -n "$expect_branch" ] || expect_branch=$(git rev-parse --abbrev-ref HEAD)
[ -n "$expect_sha" ] || expect_sha=$(git rev-parse HEAD)

args=(--expect-branch "$expect_branch" --expect-sha "$expect_sha")
for m in "${messages[@]}"; do args+=(-m "$m"); done
args+=(${pass[@]+"${pass[@]}"})

if [ "$own_ranges" -eq 1 ]; then
  for f in "${files[@]}"; do
    # `|| true`: a file hunk-ranges cannot read yields no flag, and commit-pathspec.sh then
    # applies its own untracked/deleted handling to it.
    out=$(bash "$ranges_sh" "$f" 2>/dev/null) || true
    while IFS= read -r line; do
      case "$line" in
        "--own-range "*) args+=(--own-range "${line#--own-range }") ;;
      esac
    done <<<"$out"
  done
fi

# exec, not a call: the caller sees commit-pathspec.sh's own exit status and nothing can be
# appended after it that would mask a refusal.
exec bash "$commit_sh" -C "$repo" "${args[@]}" -- "${files[@]}"
