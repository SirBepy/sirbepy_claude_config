#!/usr/bin/env bash
# Prefilter gate: runs comment-tense.sh, em-dash.sh, secret-scan.sh; exits non-zero if any
# prints or errors, so `prefilter-gate.sh <files> && git commit ...` structurally blocks a
# flagged diff. Wraps those scripts unchanged - they still work standalone. Todo 356.
# comment-noise.sh also runs but is informational only (demoted, todo 922): its output is
# printed for visibility but never sets the exit status, so a long comment block never blocks
# a commit; the measurement stays available for todo 403's brainstorm.

# Usage: prefilter-gate.sh [-C <repo>|--repo <repo>] <file> [<file> ...]   working-tree mode
#        prefilter-gate.sh --range <base>                                  range mode, forwarded as-is
# Exit 0 = clean, 1 = a prefilter flagged something, 2 = could not run (bad path, no repo found).
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
status=0
repo=""

if [ "${1:-}" = "-C" ] || [ "${1:-}" = "--repo" ]; then
  repo="${2:-}"
  shift 2
  if ! git -C "$repo" rev-parse --show-toplevel >/dev/null 2>&1; then
    printf 'ERROR: %s is not a git repository\n' "$repo"
    exit 2
  fi
elif [ "${1:-}" != "--range" ] && [ $# -gt 0 ]; then
  # A path inside a submodule resolves to the SUBMODULE's own root, not the parent's, so
  # keying off argv[1] alone (as 447 did) leaves any other group's paths silently unresolved
  # (todo 412). Group every path by its own resolved repo instead.
  cwd_repo=$(git rev-parse --show-toplevel 2>/dev/null)
  declare -A group_paths
  # "${!group_paths[@]}" is hash-bucket order, not insertion order, so a multi-repo report
  # was not diffable run to run (todo 802). Track first-seen order in a plain array instead.
  declare -a repo_order=()
  for a in "$@"; do
    # A directory argument that IS a submodule root resolves via its own toplevel, not its
    # parent's, or the whole submodule reads back as one gitlink entry (todo 801).
    if [ -d "$a" ]; then
      arg_repo=$(git -C "$a" rev-parse --show-toplevel 2>/dev/null)
    else
      arg_repo=$(git -C "$(dirname -- "$a")" rev-parse --show-toplevel 2>/dev/null)
    fi
    if [ -z "$arg_repo" ]; then
      printf 'ERROR: could not find a git repository for %s\n' "$a"
      exit 2
    fi
    if [ "$arg_repo" = "$cwd_repo" ]; then
      # A directory that is not a submodule root can still CONTAIN one further down (`vendor/`,
      # or the repo root); reading it as a plain path would silently skip that submodule's diff.
      # Refuse instead of guessing, and name what was skipped.
      if [ -d "$a" ]; then
        subs=$(git ls-files -s -- "$a" 2>/dev/null | grep '^160000' | cut -f2-)
        if [ -n "$subs" ]; then
          printf 'ERROR: %s contains submodule(s) a directory argument cannot resolve, pass their paths directly: %s\n' \
            "$a" "$(printf '%s' "$subs" | tr '\n' ' ')"
          exit 2
        fi
      fi
      rel="$a"
    else
      # `git -C <repo> diff` resolves pathspecs against the NEW cwd, not the caller's, so a
      # parent-relative path silently misses once forwarded - rebuild it relative to its own root.
      if [ -d "$a" ]; then
        prefix=$(git -C "$a" rev-parse --show-prefix 2>/dev/null)
        rel="${prefix%/}"
        [ -z "$rel" ] && rel="."
      else
        prefix=$(git -C "$(dirname -- "$a")" rev-parse --show-prefix 2>/dev/null)
        rel="${prefix}$(basename -- "$a")"
      fi
    fi
    if [ -z "${group_paths[$arg_repo]+_}" ]; then
      repo_order+=("$arg_repo")
    fi
    group_paths["$arg_repo"]+="$rel"$'\n'
  done

  # cwd's section is the byte-identical hot path readers expect at the top; everything else
  # follows in the order its first path argument appeared.
  ordered_keys=()
  if [ -n "$cwd_repo" ] && [ -n "${group_paths[$cwd_repo]+_}" ]; then
    ordered_keys+=("$cwd_repo")
  fi
  for repo_key in "${repo_order[@]}"; do
    [ "$repo_key" = "$cwd_repo" ] || ordered_keys+=("$repo_key")
  done

  for repo_key in "${ordered_keys[@]}"; do
    readarray -t rels <<<"${group_paths[$repo_key]}"
    paths=()
    for r in "${rels[@]}"; do [ -n "$r" ] && paths+=("$r"); done
    for script in comment-tense.sh em-dash.sh secret-scan.sh; do
      if [ "$repo_key" = "$cwd_repo" ]; then
        out=$(bash "$dir/$script" "${paths[@]}")
      else
        out=$(bash "$dir/$script" --repo "$repo_key" "${paths[@]}")
      fi
      rc=$?
      if [ -n "$out" ] || [ "$rc" -ne 0 ]; then
        # cwd's own repo prints the plain header so this stays byte-identical to before todo
        # 412; a forwarded repo (submodule or otherwise) names itself in the header.
        if [ "$repo_key" = "$cwd_repo" ]; then
          printf '=== %s ===\n%s\n' "$script" "$out"
        else
          printf '=== %s (%s) ===\n%s\n' "$script" "$repo_key" "$out"
        fi
        status=1
      fi
    done
    # comment-noise.sh is informational only (demoted, todo 922): run it, print anything it
    # says, but never let it set status - a long comment block no longer blocks a commit.
    if [ "$repo_key" = "$cwd_repo" ]; then
      noise_out=$(bash "$dir/comment-noise.sh" "${paths[@]}")
    else
      noise_out=$(bash "$dir/comment-noise.sh" --repo "$repo_key" "${paths[@]}")
    fi
    if [ -n "$noise_out" ]; then
      if [ "$repo_key" = "$cwd_repo" ]; then
        printf '=== comment-noise.sh (informational, non-blocking) ===\n%s\n' "$noise_out"
      else
        printf '=== comment-noise.sh (informational, non-blocking) (%s) ===\n%s\n' "$repo_key" "$noise_out"
      fi
    fi
  done
  exit $status
fi

for script in comment-tense.sh em-dash.sh secret-scan.sh; do
  if [ -n "$repo" ]; then
    out=$(bash "$dir/$script" --repo "$repo" "$@")
  else
    out=$(bash "$dir/$script" "$@")
  fi
  rc=$?
  if [ -n "$out" ] || [ "$rc" -ne 0 ]; then
    printf '=== %s ===\n%s\n' "$script" "$out"
    status=1
  fi
done

# comment-noise.sh is informational only (demoted, todo 922): see the loop above for why.
if [ -n "$repo" ]; then
  noise_out=$(bash "$dir/comment-noise.sh" --repo "$repo" "$@")
else
  noise_out=$(bash "$dir/comment-noise.sh" "$@")
fi
if [ -n "$noise_out" ]; then
  printf '=== comment-noise.sh (informational, non-blocking) ===\n%s\n' "$noise_out"
fi

exit $status
