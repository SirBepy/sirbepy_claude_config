#!/usr/bin/env bash
# Scripts /commit step 8's fixed per-commit chain (todo 964) so an orchestrator stops
# hand-composing it: prefilter gate, branch guard, HEAD guard, overlap-check, foreign-hunk-check
# (own-ranges auto-derived from `git diff HEAD` when --own-range is omitted - todo 924/933, the
# same per-hunk arithmetic SKILL.md step 8 describes doing by eye), staged-pathspec coverage
# check, the commit, then `git rev-parse HEAD` on its own last line.
#
# This script ADVISES AND VERIFIES, it never DECIDES: every check that SKILL.md step 8 treats as
# a judgement call (an overlap hit, a foreign hunk, a possible half-committed move, a moved HEAD)
# stops the run by default and prints exactly what a human/orchestrator needs to decide. Once
# decided, rerun with the matching --force <check> to proceed past THAT check only - branch-guard
# and the prefilter gate accept no override, matching step 8's own "never bypass" wording.
#
# Usage:
#   commit-pathspec.sh [-C|--repo <repo>] --expect-branch <b> --expect-sha <sha>
#     [--own <sha,sha,...>] [--own-range <file>:<a>-<b>[,<a>-<b>...]]...
#     [--force <check>[,<check>...]] -m <message> -- <file> [<file> ...]
#
# --own-range is OPTIONAL per file: when a file has no explicit range, this script derives it
# from the file's own current `@@` hunk headers and treats every hunk as own (the same "1-9999"
# assumption step 8 already made implicitly, now stated on its own printed line instead of typed
# by hand). Give --own-range explicitly only for a genuinely mixed file (a hunk you did not
# write) - the auto path cannot know about a hunk it was never told to exclude.
#
# --force values: head-guard, overlap, foreign-hunk, coverage. Never: branch-guard, prefilter.
#
# Exit 0: committed, full sha printed on the last line. Exit 1: a check refused (nothing
# committed) - the printed verdict says what to decide. Exit 2: could not run (bad args/repo/git
# failure) - not a finding, fix and rerun.
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

repo_in=""
expect_branch=""
expect_sha=""
own_shas=""
declare -A explicit_ranges
force_list=""
message=""
files=()

while [ $# -gt 0 ]; do
  case "$1" in
    -C|--repo) repo_in="${2:-}"; shift 2 ;;
    --expect-branch) expect_branch="${2:-}"; shift 2 ;;
    --expect-sha) expect_sha="${2:-}"; shift 2 ;;
    --own) own_shas="${2:-}"; shift 2 ;;
    --own-range)
      spec="${2:-}"; shift 2
      key="${spec%%:*}"
      explicit_ranges["$key"]+="${spec#*:},"
      ;;
    --force) force_list="${2:-}"; shift 2 ;;
    -m|--message) message="${2:-}"; shift 2 ;;
    --) shift; files=("$@"); break ;;
    *) printf 'ERROR: unknown argument %s\n' "$1"; exit 2 ;;
  esac
done

if [ -z "$expect_branch" ] || [ -z "$expect_sha" ] || [ -z "$message" ] || [ "${#files[@]}" -eq 0 ]; then
  printf 'ERROR: --expect-branch, --expect-sha, -m and -- <files> are all required\n'
  exit 2
fi

if [ -n "$force_list" ]; then
  IFS=',' read -r -a force_arr <<<"$force_list"
  for c in "${force_arr[@]}"; do
    case "$c" in
      head-guard|overlap|foreign-hunk|coverage) ;;
      branch-guard|prefilter|prefilter-gate)
        printf 'ERROR: --force %s is never accepted - branch-guard and the prefilter gate are not overridable\n' "$c"
        exit 2 ;;
      *)
        printf 'ERROR: unknown --force check name %s (valid: head-guard, overlap, foreign-hunk, coverage)\n' "$c"
        exit 2 ;;
    esac
  done
fi
has_force() { [[ ",$force_list," == *",$1,"* ]]; }

repo_check="${repo_in:-.}"
if ! git -C "$repo_check" rev-parse --show-toplevel >/dev/null 2>&1; then
  printf 'ERROR: %s is not a git repository\n' "$repo_check"
  exit 2
fi
repo_root=$(git -C "$repo_check" rev-parse --show-toplevel)
git_c() { git -C "$repo_root" "$@"; }

# Per-hunk `@@ -a,b +c,d @@` -> own range c-(c+d-1), the exact hand conversion SKILL.md step 8
# describes; a pure-deletion hunk (+c,0) contributes no new-file lines and is skipped, matching
# foreign-hunk-check.sh's own treatment of that case.
derive_own_ranges() {
  local diff_out="$1" ranges="" line rest newspec c d end
  while IFS= read -r line; do
    [[ "$line" == '@@ -'* ]] || continue
    rest=${line#*+}
    newspec=${rest%% @@*}
    c=${newspec%%,*}
    if [ "$newspec" = "$c" ]; then d=1; else d=${newspec#*,}; fi
    [ "$d" -eq 0 ] && continue
    end=$((c + d - 1))
    ranges+="${c}-${end},"
  done <<<"$diff_out"
  printf '%s' "${ranges%,}"
}

# live/untracked/deleted-staged/deleted-unstaged/unknown. Neither overlap-check.sh nor
# foreign-hunk-check.sh understands a deleted path (both crash or misreport on one, the second
# defect this script exists to remove) - deleted-staged is the case with nothing left to diff,
# so it is excluded from both checks' file lists below but still reaches the commit pathspec.
classify_path() {
  local f="$1"
  if [ -e "$repo_root/$f" ]; then
    if git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then echo live; else echo untracked; fi
    return
  fi
  if [ "$(git_c diff --cached --name-status -- "$f" 2>/dev/null | cut -f1)" = "D" ]; then
    echo deleted-staged
  elif git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    echo deleted-unstaged
  else
    echo unknown
  fi
}

declare -A class_of
diffable_files=()
for f in "${files[@]}"; do
  c=$(classify_path "$f")
  class_of["$f"]="$c"
  if [ "$c" = "unknown" ]; then
    printf 'ERROR: %s is not on disk, not in the index, and not staged for deletion in %s\n' "$f" "$repo_root"
    exit 2
  fi
  [ "$c" != "deleted-staged" ] && diffable_files+=("$f")
done

echo "=== commit-pathspec: $repo_root ==="
printf '[pathspec] classification:\n'
for f in "${files[@]}"; do
  note=""
  [ "${class_of[$f]}" = "deleted-staged" ] && note=" (excluded from overlap-check/foreign-hunk-check - nothing left to diff)"
  printf '  - %s: %s%s\n' "$f" "${class_of[$f]}" "$note"
done

# --- prefilter gate (step 5a) - never overridable ---
pf_out=$(bash "$dir/prefilter-gate.sh" -C "$repo_root" "${files[@]}" 2>&1); pf_rc=$?
if [ "$pf_rc" -eq 2 ]; then
  printf '[prefilter-gate] ERROR (could not run):\n%s\n' "$pf_out"
  exit 2
elif [ "$pf_rc" -ne 0 ]; then
  printf '[prefilter-gate] FLAGGED (fix the added line(s) and rerun, never overridable):\n%s\n' "$pf_out"
  exit 1
else
  printf '[prefilter-gate] clean\n'
fi

# --- branch guard - never overridable, a wrong branch means the wrong commit target ---
actual_branch=$(git_c rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -z "$actual_branch" ]; then
  printf '[branch-guard] ERROR: could not resolve current branch\n'
  exit 2
fi
if [ "$actual_branch" = "HEAD" ] || [ "$actual_branch" != "$expect_branch" ]; then
  printf '[branch-guard] REFUSED: expected %s, HEAD is on %s (never overridable)\n' "$expect_branch" "$actual_branch"
  exit 1
fi
printf '[branch-guard] OK (on %s)\n' "$actual_branch"

# --- HEAD guard - a peer commit landing here is a judgement call (SKILL.md step 8), not a fact
# this script can resolve on its own ---
actual_sha=$(git_c rev-parse HEAD 2>/dev/null)
if [ -z "$actual_sha" ]; then
  printf '[head-guard] ERROR: could not resolve HEAD\n'
  exit 2
fi
if [ "$actual_sha" != "$expect_sha" ]; then
  if has_force head-guard; then
    printf '[head-guard] OVERRIDDEN (--force head-guard): expected %s, HEAD is now %s\n' "$expect_sha" "$actual_sha"
  else
    printf '[head-guard] REFUSED: expected %s, HEAD is now %s - decide per SKILL.md step 8 (announce and proceed, narrow the pathspec, or ask), then rerun with --force head-guard if proceeding\n' "$expect_sha" "$actual_sha"
    exit 1
  fi
else
  printf '[head-guard] OK (HEAD matches expected %s)\n' "$expect_sha"
fi

# --- unpushed-overlap check (hunk-level, own shas excluded) ---
if [ "${#diffable_files[@]}" -eq 0 ]; then
  printf '[overlap-check] skipped (every pathspec file is an already-staged deletion)\n'
else
  own_args=()
  [ -n "$own_shas" ] && own_args=(--own "$own_shas")
  ov_out=$(bash "$dir/overlap-check.sh" -C "$repo_root" "${own_args[@]}" "${diffable_files[@]}" 2>&1); ov_rc=$?
  if [ "$ov_rc" -eq 2 ]; then
    printf '[overlap-check] ERROR (could not run):\n%s\n' "$ov_out"
    exit 2
  elif [ "$ov_rc" -ne 0 ]; then
    if has_force overlap; then
      printf '[overlap-check] OVERRIDDEN (--force overlap):\n%s\n' "$ov_out"
    else
      printf '[overlap-check] REFUSED (judgement call - see SKILL.md step 8, "On exit 1, evaluate in this order"):\n%s\n' "$ov_out"
      exit 1
    fi
  else
    printf '[overlap-check] clean:\n%s\n' "$ov_out"
  fi
fi

# --- working-tree foreign-hunk check, own-ranges derived automatically unless declared ---
fh_files=()
fh_own_args=()
derive_notes=""
for f in "${diffable_files[@]}"; do
  if [ "${class_of[$f]}" = "untracked" ]; then
    diff_out=$(git_c diff --no-index -- /dev/null "$f" 2>/dev/null)
  else
    diff_out=$(git_c diff HEAD -- "$f")
  fi
  [ -z "$diff_out" ] && continue
  if [ -n "${explicit_ranges[$f]:-}" ]; then
    spec="${explicit_ranges[$f]%,}"
    derive_notes+="  - $f: caller-declared own-range $spec"$'\n'
  else
    spec=$(derive_own_ranges "$diff_out")
    if [ -z "$spec" ]; then
      derive_notes+="  - $f: pure deletion, no new-file lines to own, skipped for this check"$'\n'
      continue
    fi
    derive_notes+="  - $f: auto-derived own-range $spec (every current hunk assumed own, todo 924/933)"$'\n'
  fi
  fh_files+=("$f")
  fh_own_args+=(--own "$f:$spec")
done
printf '[own-range] derivation:\n%s' "${derive_notes:-  (nothing to derive)$'\n'}"

if [ "${#fh_files[@]}" -eq 0 ]; then
  printf '[foreign-hunk-check] skipped (no file has new-file content to check)\n'
else
  fh_out=$(bash "$dir/foreign-hunk-check.sh" -C "$repo_root" "${fh_own_args[@]}" "${fh_files[@]}" 2>&1); fh_rc=$?
  if [ "$fh_rc" -eq 2 ]; then
    printf '[foreign-hunk-check] ERROR (could not run):\n%s\n' "$fh_out"
    exit 2
  elif [ "$fh_rc" -ne 0 ]; then
    if has_force foreign-hunk; then
      printf '[foreign-hunk-check] OVERRIDDEN (--force foreign-hunk):\n%s\n' "$fh_out"
    else
      printf '[foreign-hunk-check] REFUSED (judgement call - see SKILL.md step 8 and edge-cases.md "Foreign hunk inside your own hunk"):\n%s\n' "$fh_out"
      exit 1
    fi
  else
    printf '[foreign-hunk-check] clean:\n%s\n' "$fh_out"
  fi
fi

# --- staged-pathspec coverage check: a half-committed move stages an add and a delete, and
# naming only the destination silently commits the copy while the delete rides along unreported
# ---
declare -A in_pathspec
for f in "${files[@]}"; do in_pathspec["$f"]=1; done
coverage_move=()
coverage_other=()
check_coverage_hit() {
  local p="$1" pd d f
  [ -n "${in_pathspec[$p]:-}" ] && return
  pd=$(dirname -- "$p")
  for f in "${files[@]}"; do
    d=$(dirname -- "$f")
    if [ "$d" = "$pd" ]; then
      coverage_move+=("$p")
      return
    fi
  done
  coverage_other+=("$p")
}
staged=$(git_c diff --cached --name-status)
while IFS=$'\t' read -r status path rest; do
  [ -z "$path" ] && continue
  if [[ "$status" == R* ]]; then
    check_coverage_hit "$path"
    check_coverage_hit "$rest"
  else
    check_coverage_hit "$path"
  fi
done <<<"$staged"

if [ "${#coverage_move[@]}" -gt 0 ]; then
  if has_force coverage; then
    printf '[coverage-check] OVERRIDDEN (--force coverage): staged path(s) sharing a directory with the pathspec are not in it: %s\n' "${coverage_move[*]}"
  else
    printf '[coverage-check] REFUSED: staged path(s) sharing a directory with the pathspec are not in it (possible half-committed move) - widen the pathspec, or rerun with --force coverage if deliberately leaving it behind: %s\n' "${coverage_move[*]}"
    exit 1
  fi
fi
if [ "${#coverage_other[@]}" -gt 0 ]; then
  printf '[coverage-check] warning, non-blocking (unrelated directory, likely another session'"'"'s own staged work): %s\n' "${coverage_other[*]}"
fi
if [ "${#coverage_move[@]}" -eq 0 ] && [ "${#coverage_other[@]}" -eq 0 ]; then
  printf '[coverage-check] clean\n'
fi

# --- commit by pathspec, never stage-then-commit ---
for f in "${files[@]}"; do
  if [ "${class_of[$f]}" = "untracked" ]; then
    if ! git_c add -- "$f" >/dev/null 2>&1; then
      printf '[commit] ERROR: could not stage untracked file %s\n' "$f"
      exit 2
    fi
  fi
done
if ! commit_out=$(git_c commit -m "$message" -- "${files[@]}" 2>&1); then
  printf '[commit] ERROR: git commit failed:\n%s\n' "$commit_out"
  exit 2
fi
printf '[commit] committed\n'
git_c rev-parse HEAD
