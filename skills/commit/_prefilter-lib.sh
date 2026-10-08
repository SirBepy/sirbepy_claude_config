#!/usr/bin/env bash
# git_c and its --repo arg parse, shared by skills/commit/*.sh (todo 447, centralised by 813).
# Dot-sourced by path, not imported. repo="" here so git_c works pre-parse (em-dash.sh --range).
repo=""
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

# A function's `shift` can't reach the caller's $@, so the trimmed list comes back via
# PREFILTER_ARGS; caller restores with `set -- "${PREFILTER_ARGS[@]}"`. `-C` is accepted
# alongside `--repo` because overlap-check.sh and foreign-hunk-check.sh's own usage comments
# document both, and commit-pathspec.sh calls them with `-C` (todo 912).
parse_repo_arg() {
  if [ "${1:-}" = "-C" ] || [ "${1:-}" = "--repo" ]; then repo="$2"; shift 2; fi
  PREFILTER_ARGS=("$@")
}

# A path git cannot see (gitignored, or missing) yields no diff from the tracked/untracked
# sources a caller already gathers, reading as "clean" though nothing was seen (todo 460).
# Classifies each argument and prints invisible ones' diff via --no-index. Dot-sourced, so
# "$@" passes straight through - no array-return/quoting boundary to cross (804's named risk).
scan_invisible_paths() {
  local a out rc
  for a in "$@"; do
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
  # od's hex pairs stay whitespace-delimited tokens here deliberately - stripping the
  # separators first (as an earlier version of this check did) lets two adjacent non-NUL
  # bytes' digits align into a spurious "00", e.g. a space (20) before a newline (0a)
  # concatenates to "200a", which itself contains "00" with no null byte anywhere.
  head -c 8000 -- "$p" | od -An -tx1 -v | tr -s ' \n' '\n' | grep -qx '00'
}

# Routes a binary path into a caller's AWK-built skip set rather than reshaping its
# diff-gathering calls - every caller already keys "skip" off the '+++ b/<key>' header, so
# reusing that path avoids a second file-list-filtering mechanism (todo 986).
binary_list() {
  local f p key
  for f in "$@"; do
    is_binary_path "$f" || continue
    printf 'skipped binary: %s\n' "$f" >&2
    key=$(git_c ls-files --full-name -- "$f" 2>/dev/null)
    [ -z "$key" ] && key=$(git_c ls-files --others --exclude-standard --full-name -- "$f" 2>/dev/null)
    printf '%s\n' "${key:-$f}"
  done
}
