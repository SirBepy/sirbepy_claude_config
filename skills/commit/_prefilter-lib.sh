#!/usr/bin/env bash
# git_c and its --repo arg parse, shared by skills/commit/*.sh (todo 447, centralised by 813).
# Dot-sourced by path, not imported. repo="" here so git_c works pre-parse (em-dash.sh --range).
repo=""
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

# A function's `shift` can't reach the caller's $@, so the trimmed list comes back via
# PREFILTER_ARGS; caller restores with `set -- "${PREFILTER_ARGS[@]}"`.
parse_repo_arg() {
  if [ "${1:-}" = "--repo" ]; then repo="$2"; shift 2; fi
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
