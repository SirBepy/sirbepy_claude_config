#!/usr/bin/env bash
# git_c and its --repo arg parse, shared by skills/commit/*.sh (todo 447, centralised by 813).
# Dot-sourced by path, not imported. repo="" here so git_c works pre-parse (em-dash.sh --range).
repo=""
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

# Windows caps one command line near 32K characters, and a generated-asset commit names more
# paths than that. Everything below that hands the whole path list to an external command either
# splits it at this many characters or moves it through a file; PREFILTER_ARGV_BUDGET lets a test
# force the split with a handful of paths.
PREFILTER_ARGV_BUDGET="${PREFILTER_ARGV_BUDGET:-12000}"

# A function's `shift` can't reach the caller's $@, so the trimmed list comes back via
# PREFILTER_ARGS; caller restores with `set -- "${PREFILTER_ARGS[@]}"`. `-C` is accepted
# alongside `--repo` because overlap-check.sh and foreign-hunk-check.sh's own usage comments
# document both, and commit-pathspec.sh calls them with `-C` (todo 912).
# `--paths-from-file <f>` (NUL-separated) appends the file's paths to the list: how
# prefilter-gate.sh hands a path list that would not fit on one command line to each script.
parse_repo_arg() {
  local pf="" p
  while true; do
    case "${1:-}" in
      -C|--repo) repo="$2"; shift 2 ;;
      --paths-from-file) pf="$2"; shift 2 ;;
      *) break ;;
    esac
  done
  PREFILTER_ARGS=("$@")
  if [ -n "$pf" ]; then
    while IFS= read -r -d '' p; do PREFILTER_ARGS+=("$p"); done < "$pf"
  fi
}

# True when "$@" would not fit in one external command's argv budget.
paths_over_budget() {
  local p total=0
  for p in "$@"; do
    total=$((total + ${#p} + 1))
    [ "$total" -gt "$PREFILTER_ARGV_BUDGET" ] && return 0
  done
  return 1
}

# Sets DEDUPED to "$@" minus every path that sits under another argument which is a directory.
# git walks a directory pathspec itself, so a caller that names a directory AND each file in it
# (commit-pathspec.sh does) would get those files' diffs twice once the list is split across calls.
_dedupe_under_dirs() {
  local p base d keep dirs=()
  for p in "$@"; do
    base="${p%/}"
    [ -n "$base" ] && [ "$base" != "." ] || continue
    case "$p" in
      /*|?:[/\\]*) [ -d "$p" ] && dirs+=("$base") ;;
      *) [ -d "${repo:+$repo/}$p" ] && dirs+=("$base") ;;
    esac
  done
  DEDUPED=()
  if [ "${#dirs[@]}" -eq 0 ]; then DEDUPED=("$@"); return; fi
  for p in "$@"; do
    keep=1
    for d in "${dirs[@]}"; do
      case "$p" in "$d"/*) keep=0; break ;; esac
    done
    [ "$keep" -eq 1 ] && DEDUPED+=("$p")
  done
}

# git_c_paths <git args...> -- <paths...>: `git_c <git args> -- <paths>`, split over argv-sized
# chunks when the path list is too long for one command line. Chunks never repeat a path, so the
# concatenated output equals one call's output.
git_c_paths() {
  local args=() chunk=() len=0 p
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do args+=("$1"); shift; done
  [ $# -gt 0 ] && shift
  if [ $# -eq 0 ] || ! paths_over_budget "$@"; then
    git_c "${args[@]}" -- "$@"
    return
  fi
  _dedupe_under_dirs "$@"
  set -- "${DEDUPED[@]}"
  for p in "$@"; do
    if [ "${#chunk[@]}" -gt 0 ] && [ $((len + ${#p} + 1)) -gt "$PREFILTER_ARGV_BUDGET" ]; then
      git_c "${args[@]}" -- "${chunk[@]}"
      chunk=(); len=0
    fi
    chunk+=("$p"); len=$((len + ${#p} + 1))
  done
  if [ "${#chunk[@]}" -gt 0 ]; then git_c "${args[@]}" -- "${chunk[@]}"; fi
  return 0
}

# awk -v puts the whole exempt list on the command line, which a few hundred binary paths push
# past the Windows limit; the awk programs read it from this file instead. Prints the file's path.
write_exempt_file() {
  local f
  f=$(mktemp) || return 1
  printf '%s\n' "$1" > "$f"
  printf '%s' "$f"
}

# A path git cannot see (gitignored, or missing) yields no diff from the tracked/untracked
# sources a caller already gathers, reading as "clean" though nothing was seen (todo 460).
# Classifies each argument and prints invisible ones' diff via --no-index. Dot-sourced, so
# "$@" passes straight through - no array-return/quoting boundary to cross (804's named risk).
#
# With many arguments the common case (a path git already lists) is answered from two listings
# instead of two git calls per path; any argument a listing does not name exactly (a directory, a
# gitignored file, an odd spelling) still takes the per-path check below.
scan_invisible_paths() {
  local a out rc f
  local -A listed=()
  if [ "$#" -gt 1 ]; then
    while IFS= read -r -d '' f; do listed["$f"]=1; done < <(
      git_c_paths ls-files -z -- "$@"
      git_c_paths ls-files -z --others --exclude-standard -- "$@"
    )
  fi
  for a in "$@"; do
    [ -n "${listed["$a"]:-}" ] && continue
    if git_c ls-files --error-unmatch -- "$a" >/dev/null 2>&1; then continue; fi
    if [ -n "$(git_c ls-files --others --exclude-standard -- "$a")" ]; then continue; fi
    out=$(git_c diff --no-index -- /dev/null "$a" 2>&1); rc=$?
    if [ "$rc" -gt 1 ]; then
      printf 'ERROR: could not inspect invisible file %s (git diff --no-index exit %d): %s\n' "$a" "$rc" "$out"
    else
      printf '%s\n' "$out"
    fi
  done
}

# A text-heavy binary (PDF, font) can clear 8KB with no NUL byte, so git's own `+++ /dev/null`
# vs real-diff heuristic (used by callers below for untracked files) still emits it as scannable
# text (todo 986). Extension is checked first since that is the exact shape that slipped through;
# the NUL sniff backs it up for an extensionless binary. Shared by every prefilter (todo 1086) so
# em-dash.sh and secret-scan.sh can never drift on which files are binary.
BINARY_EXT_RE='\.(pdf|png|jpe?g|gif|webp|ico|ttf|otf|woff2?|mp3|mp4|zip)$'
is_binary_path() {
  local f="$1" p stats
  printf '%s' "$f" | grep -qiE "$BINARY_EXT_RE" && return 0
  if git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    stats=$(git_c diff HEAD --numstat -- "$f" 2>/dev/null)
  else
    stats=$(git_c diff --no-index --numstat -- /dev/null "$f" 2>/dev/null)
  fi
  case "$stats" in -$'\t'-$'\t'*) return 0 ;; esac
  case "$f" in /*|?:[/\\]*) p="$f" ;; *) p="${repo:+$repo/}$f" ;; esac
  [ -f "$p" ] || return 1
  has_early_nul "$p"
}

# True when one of the first 8000 bytes of "$1" is NUL, the window git's own binary sniff reads.
# `read -n 8000 -d ''` stops at the first NUL or after 8000 bytes, whichever comes first, and
# returns 0 either way (1 only on EOF before both), so a NUL in the window is exactly "status 0 and
# fewer than 8000 bytes read". No process is spawned, which is what keeps a 1000-file sniff cheap.
# The earlier head|od|tr|grep pipeline gave identical answers at the 7999/8000/8001 byte edges.
has_early_nul() {
  local chunk rc
  local LC_ALL=C IFS=
  read -r -d '' -n 8000 chunk 2>/dev/null < "$1"
  rc=$?
  [ "$rc" -eq 0 ] && [ "${#chunk}" -lt 8000 ]
}

_ext_is_binary() { [[ "${1,,}" =~ $BINARY_EXT_RE ]]; }

# Routes a binary path into a caller's AWK-built skip set rather than reshaping its
# diff-gathering calls - every caller already keys "skip" off the '+++ b/<key>' header, so
# reusing that path avoids a second file-list-filtering mechanism (todo 986).
#
# Plain relative file paths (the shape commit-pathspec.sh expands a directory into) are judged in
# bulk: extension, then one `diff HEAD --numstat` listing for tracked binaries, then the NUL sniff
# above. An untracked file's verdict is the NUL sniff alone, which is what git's own no-index
# numstat reduces to for it apart from a .gitattributes -diff marking, and such a file prints no
# '+' lines to scan anyway. Directories, absolute or oddly spelled paths, and a repo rooted in a
# subdirectory keep the per-path check, so their verdicts are unchanged.
binary_list() {
  local f rec fast=0
  local -a bulk=() cands=()
  local -A tracked_bin=()
  [ -z "$(git_c rev-parse --show-prefix 2>/dev/null)" ] && fast=1
  for f in "$@"; do
    case "$f" in
      /*|?:[/\\]*|./*|../*|*\\*|*[\*\?\[]*|"") _binary_list_one "$f"; continue ;;
    esac
    if [ "$fast" -ne 1 ] || [ -d "${repo:+$repo/}$f" ]; then _binary_list_one "$f"; continue; fi
    bulk+=("$f")
    _ext_is_binary "$f" || cands+=("$f")
  done
  if [ "${#cands[@]}" -gt 0 ]; then
    while IFS= read -r -d '' rec; do
      case "$rec" in -$'\t'-$'\t'*) tracked_bin["${rec#-$'\t'-$'\t'}"]=1 ;; esac
    done < <(git_c_paths diff HEAD --numstat -z --no-renames -- "${cands[@]}" 2>/dev/null)
  fi
  for f in "${bulk[@]}"; do
    if _ext_is_binary "$f" || [ -n "${tracked_bin["$f"]:-}" ] || { [ -f "${repo:+$repo/}$f" ] && has_early_nul "${repo:+$repo/}$f"; }; then
      printf 'skipped binary: %s\n' "$f" >&2
      printf '%s\n' "$f"
    fi
  done
}

_binary_list_one() {
  local f="$1" key
  is_binary_path "$f" || return 0
  printf 'skipped binary: %s\n' "$f" >&2
  key=$(git_c ls-files --full-name -- "$f" 2>/dev/null)
  [ -z "$key" ] && key=$(git_c ls-files --others --exclude-standard --full-name -- "$f" 2>/dev/null)
  printf '%s\n' "${key:-$f}"
}

# `git diff --no-index -- /dev/null <f>` for every untracked, non-ignored file under "$@": the
# untracked half of every prefilter's diff stream. One git call per file costs ~0.03s of process
# spawn each on Windows, which a 1000-file commit pays four times over, so the files are registered
# intent-to-add in a throwaway index and diffed against the empty tree in one call, which prints the
# same new-file diffs and writes nothing to the repo's index or object store. Anything the batch
# cannot reproduce exactly (a nested-repo directory entry, a repo rooted in a subdirectory, any git
# failure) falls back to the per-file loop.
untracked_diffs() {
  local list f out rc
  list=$(mktemp) || return 1
  git_c_paths ls-files --others --exclude-standard -z -- "$@" > "$list"
  if [ -s "$list" ] && ! _untracked_diffs_batched "$list"; then
    while IFS= read -r -d '' f; do
      out=$(git_c diff --no-index -- /dev/null "$f" 2>&1); rc=$?
      if [ "$rc" -gt 1 ]; then
        printf 'ERROR: could not inspect untracked file %s (git diff --no-index exit %d): %s\n' "$f" "$rc" "$out"
      else
        printf '%s\n' "$out"
      fi
    done < "$list"
  fi
  rm -f "$list"
}

_untracked_diffs_batched() {
  local idx out tree
  grep -zq '/$' "$1" && return 1
  [ -z "$(git_c rev-parse --show-prefix 2>/dev/null)" ] || return 1
  tree=$(git_c hash-object -t tree /dev/null 2>/dev/null) || return 1
  idx=$(mktemp -u) || return 1
  out=$(mktemp) || return 1
  if GIT_LITERAL_PATHSPECS=1 GIT_INDEX_FILE="$idx" git_c add -N --pathspec-from-file="$1" --pathspec-file-nul >/dev/null 2>&1 \
     && GIT_INDEX_FILE="$idx" git_c diff "$tree" > "$out" 2>/dev/null; then
    cat "$out"
    rm -f "$idx" "$idx.lock" "$out"
    return 0
  fi
  rm -f "$idx" "$idx.lock" "$out"
  return 1
}
