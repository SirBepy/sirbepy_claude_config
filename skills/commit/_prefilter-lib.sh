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
