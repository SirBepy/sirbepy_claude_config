#!/usr/bin/env bash
# Working-tree foreign-hunk check (todo 806): the working-tree half overlap-check.sh's --own
# doesn't cover. Nothing here is committed, so ownership can't come from blame - the caller
# supplies the line ranges THIS session edited; every other line in the diff is foreign.

# Usage: foreign-hunk-check.sh [-C|--repo <repo>] --own <file>:<a>-<b>[,<a>-<b>...] <file> ...
# --own is repeatable, new-file numbering (git diff's + side); no --own for a pathspec file
# reports its whole diff as foreign. A pure-deletion hunk (+c,0) has no new-file lines to
# check and is skipped.

# Exit 0 clean. Exit 1: "foreign-hunks-present <range>" (separate hunk) or
# "foreign-hunks-inside-your-hunk <range>" (shares an @@ with yours, apply --cached can't
# split it, see edge-cases.md). Exit 2 could not run.
set -uo pipefail

repo=""
declare -A own_ranges
while [ $# -gt 0 ]; do
  case "$1" in
    -C|--repo) repo="${2:-}"; shift 2 ;;
    --own)
      spec="${2:-}"; shift 2
      key="${spec%%:*}"
      own_ranges["$key"]+="${spec#*:},"
      ;;
    *) break ;;
  esac
done
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

if [ $# -eq 0 ]; then
  printf 'ERROR: no files given\n'
  exit 2
fi
if ! git_c rev-parse --show-toplevel >/dev/null 2>&1; then
  printf 'ERROR: %s is not a git repository\n' "${repo:-.}"
  exit 2
fi

# Is new-file line $1 covered by any "a-b" range in the comma-joined spec $2?
line_is_own() {
  local ln="$1" spec="$2" part a b
  IFS=',' read -r -a parts <<<"$spec"
  for part in "${parts[@]}"; do
    [ -z "$part" ] && continue
    a="${part%-*}"; b="${part#*-}"
    [ "$ln" -ge "$a" ] && [ "$ln" -le "$b" ] && return 0
  done
  return 1
}

status=0
for f in "$@"; do
  spec="${own_ranges[$f]:-}"
  if git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    diff_out=$(git_c diff HEAD -- "$f")
  else
    diff_out=$(git_c diff --no-index -- /dev/null "$f" 2>/dev/null)
  fi

  if [ -z "$spec" ]; then
    if [ -n "$diff_out" ]; then
      printf '%s: no own-ranges given, treating entire diff as foreign\n' "$f"
      status=1
    else
      printf '%s: clean (no diff)\n' "$f"
    fi
    continue
  fi

  foreign_ranges=()
  mixed_ranges=()
  in_hunk=0; c=0; d=0; end=0; ln=0; own_ct=0; foreign_ct=0
  # Context lines (' ') advance ln but are neither own nor foreign - only '+' lines are
  # classified, or every hunk would read as foreign just from its surrounding context.
  flush_hunk() {
    [ "$in_hunk" -eq 1 ] || return
    [ "$foreign_ct" -eq 0 ] && return
    if [ "$own_ct" -eq 0 ]; then foreign_ranges+=("$c-$end"); else mixed_ranges+=("$c-$end"); fi
  }
  while IFS= read -r line; do
    if [[ "$line" == '@@ -'* ]]; then
      flush_hunk
      # Isolate the "+c[,d]" side the same way overlap-check.sh isolates "-a[,b]": cut at the
      # literal + (not glob here, extglob is off) then at the closing " @@".
      rest=${line#*+}
      newspec=${rest%% @@*}
      c=${newspec%%,*}
      if [ "$newspec" = "$c" ]; then d=1; else d=${newspec#*,}; fi
      end=$((c + d - 1)); ln=$c; own_ct=0; foreign_ct=0; in_hunk=1
      continue
    fi
    [ "$in_hunk" -eq 1 ] || continue
    case "$line" in
      '+'*)
        if line_is_own "$ln" "$spec"; then own_ct=$((own_ct + 1)); else foreign_ct=$((foreign_ct + 1)); fi
        ln=$((ln + 1)) ;;
      '-'*) ;;
      *) ln=$((ln + 1)) ;;
    esac
  done <<<"$diff_out"
  flush_hunk

  # Both categories are reported, never just the worse one - a separate foreign hunk elsewhere
  # in the same file is still a hunk that has to be accounted for (step 8's "every hunk" rule).
  if [ "${#mixed_ranges[@]}" -gt 0 ] || [ "${#foreign_ranges[@]}" -gt 0 ]; then
    msg="$f:"
    [ "${#mixed_ranges[@]}" -gt 0 ] && msg+=" foreign-hunks-inside-your-hunk $(IFS=,; echo "${mixed_ranges[*]}")"
    [ "${#foreign_ranges[@]}" -gt 0 ] && msg+=" foreign-hunks-present $(IFS=,; echo "${foreign_ranges[*]}")"
    printf '%s\n' "$msg"
    status=1
  else
    printf '%s: clean\n' "$f"
  fi
done

exit $status
