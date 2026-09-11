#!/usr/bin/env bash
# Scripts /commit step 8's fixed per-commit chain (todo 964) so an orchestrator stops
# hand-composing it: prefilter gate, branch guard, HEAD guard, overlap-check, foreign-hunk-check
# (own-ranges auto-derived from `git diff HEAD` when --own-range is omitted, gated on
# session-marker liveness - todo 924 REOPENED/933, the same per-hunk arithmetic SKILL.md step 8
# describes doing by eye), staged-pathspec coverage check, the commit, then `git rev-parse HEAD`
# on its own last line.
#
# This script ADVISES AND VERIFIES, it never DECIDES: every check that SKILL.md step 8 treats as
# a judgement call (an overlap hit, a foreign hunk, a possible half-committed move, a moved HEAD)
# stops the run by default and prints exactly what a human/orchestrator needs to decide. Once
# decided, rerun with the matching --force <check> to proceed past THAT check only - branch-guard
# and the prefilter gate accept no override, matching step 8's own "never bypass" wording.
#
# Usage:
#   commit-pathspec.sh [-C|--repo <repo>] --expect-branch <b> --expect-sha <sha>
#     [--own <sha,sha,...>] [--own-since <sha>] [--own-range <file>:<a>-<b>[,<a>-<b>...]]...
#     [--force <check>[,<check>...]] -m <message> -- <file> [<file> ...]
#
# --own-range is OPTIONAL per file: when a file has no explicit range, this script derives it
# from the file's own current `@@` hunk headers (the same "1-9999" assumption step 8 already made
# implicitly, now stated on its own printed line instead of typed by hand). A caller-declared
# --own-range is ALWAYS trusted, single session or not.
#
# An auto-derived range for a file that already existed at HEAD is trustworthy only when this
# session is alone in the checkout: `hooks/.session-markers/` holds one marker per live Claude
# session sharing this checkout (see the session_marker_dir block below for the exact liveness
# rule reused from `hooks/write-session-marker.ps1`), and one live marker (or zero) means every
# current hunk really is this session's own. With two or more, a peer may hold uncommitted lines
# in that same file and an auto-derived range proves nothing (todo 924 REOPENED: the check would
# just read back the exact set it was handed) - the foreign-hunk-check step then refuses by
# default instead of printing `clean`, same as any other judgement call below, and needs either a
# declared --own-range or --force foreign-hunk to proceed. A brand-new (untracked) file's
# auto-derived range stays trusted regardless of session count: it has no HEAD baseline, so there
# is no pre-existing structure for a peer's lines to hide inside, and forcing a range declaration
# on every new file in an almost-always-multi-session checkout would make the common case (all
# new files, todo 924's own Notes) constantly require --force for no real safety gain.
#
# --own-since <sha> resolves to `git log --format=%H <sha>..HEAD` and merges that sha list into
# --own (todo 978) - the retyped `git log --format=%H <session-start>..HEAD` substitution every
# caller previously rebuilt by hand before each call. It ALSO changes the foreign-hunk-check
# baseline for every file that has no explicit --own-range: the auto-derive diffs against <sha>
# instead of HEAD, so the derived range covers everything this session's own commits (sha..HEAD)
# plus its current working-tree changes to that file, not only the currently-uncommitted delta.
# That range is TRUSTED regardless of live session-marker count, the same as a caller-declared
# --own-range, because it traces to a concrete, git-verifiable commit list (git answered "what did
# sha..HEAD touch", not "what is currently sitting uncommitted") rather than the assumption the
# marker gate exists to police in the first place: that whatever is uncommitted right now must be
# this session's own. A file that also has an explicit --own-range keeps using that declared
# range instead - --own-since only fills the gap for files that would otherwise fall back to the
# HEAD-relative auto-derive.
#
# --force values: head-guard, overlap, foreign-hunk, coverage. Never: branch-guard, prefilter.
#
# Exit 0: committed, full sha printed on the last line. Exit 1: a check refused (nothing
# committed) - the printed verdict says what to decide. Exit 2: could not run (bad args/repo/git
# failure) - not a finding to act on, fix and rerun.
set -uo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

repo_in=""
expect_branch=""
expect_sha=""
own_shas=""
own_since=""
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
    --own-since) own_since="${2:-}"; shift 2 ;;
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

# --own-since resolution: a shorthand for "every commit since <sha> is mine" (todo 978). Merged
# into own_shas so overlap-check.sh's own-commit exclusion sees no difference between a hand-typed
# --own and a resolved --own-since; the foreign-hunk auto-derive baseline switch lives further
# down, where the per-file diff is actually taken.
if [ -n "$own_since" ]; then
  if ! git_c rev-parse --verify "${own_since}^{commit}" >/dev/null 2>&1; then
    printf 'ERROR: --own-since %s does not resolve to a commit in %s\n' "$own_since" "$repo_root"
    exit 2
  fi
  since_shas=$(git_c log --format=%H "${own_since}..HEAD" | tr '\n' ',' | sed 's/,$//')
  if [ -n "$since_shas" ]; then
    since_count=$(printf '%s' "$since_shas" | tr ',' '\n' | grep -c .)
    if [ -n "$own_shas" ]; then own_shas="$own_shas,$since_shas"; else own_shas="$since_shas"; fi
    printf '[own-since] resolved %s..HEAD to %d commit(s): %s\n' "$own_since" "$since_count" "$since_shas"
  else
    printf '[own-since] resolved %s..HEAD to 0 commit(s) (HEAD is at or behind %s)\n' "$own_since" "$own_since"
  fi
fi

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

# --- session-marker liveness: whether an auto-derived own-range can be trusted at all ---
# Reuses hooks/write-session-marker.ps1's own liveness contract verbatim (todo 924 REOPENED),
# rather than inventing a new one: that script prunes a marker whose session is PROVABLY dead
# (no record in ~/.claude/sessions/*.json for it, or a record whose pid no longer resolves via
# Get-Process) every time ANY session writes ITS OWN marker - pruning happens on write, not on
# read, and never on a schedule. That means a marker file present here was live as of the most
# recent marker-write anywhere in this checkout; a session that has since exited without another
# session writing a marker in between will not be pruned until that next write. That staleness
# only INFLATES the count, which pushes this check toward refusing an auto-derived range that was
# actually fine (annoying, safe) - it can never make a genuinely shared tree look like a solo one.
# This script only reads the directory: it never writes or deletes a marker.
session_marker_dir="${COMMIT_PATHSPEC_SESSION_MARKER_DIR:-$dir/../../hooks/.session-markers}"
session_marker_count=0
if [ -d "$session_marker_dir" ]; then
  # Count ONLY bare session-id markers. write-session-marker.ps1 names its file exactly
  # <session-id>, a UUID, but other tooling drops differently-named files in this same
  # directory: a silent-turns-<id> counter, and precompact-backup.py's per-session backups
  # (todo 426). Globbing everything counted those as live peers, so a session genuinely
  # alone in the tree could be refused an auto-derived range by its own leftovers.
  shopt -s nullglob
  for marker_path in "$session_marker_dir"/*; do
    case "${marker_path##*/}" in
      [0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F])
        session_marker_count=$((session_marker_count + 1)) ;;
    esac
  done
  shopt -u nullglob
fi
# Exactly one marker (this session's own) or zero (not written yet) - this session is alone, so
# every current hunk really is its own and an auto-derived range is a true "clean" verdict. Two
# or more - a peer shares the tree and an auto-derived range proves nothing.
multi_session=0
[ "$session_marker_count" -gt 1 ] && multi_session=1

# --- working-tree foreign-hunk check, own-ranges derived automatically unless declared ---
fh_files=()
fh_own_args=()
derive_notes=""
unverified_files=()
for f in "${diffable_files[@]}"; do
  if [ "${class_of[$f]}" = "untracked" ]; then
    diff_out=$(git_c diff --no-index -- /dev/null "$f" 2>/dev/null)
  elif [ -n "$own_since" ]; then
    # --own-since baseline (todo 978): everything this session's own commits (own_since..HEAD)
    # plus its current working tree changed for this file, not only the uncommitted delta.
    diff_out=$(git_c diff "$own_since" -- "$f")
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
    if [ -n "$own_since" ] && [ "${class_of[$f]}" != "untracked" ]; then
      # Traces to a concrete, git-verifiable commit list (own_since..HEAD), not an assumption
      # that whatever is currently uncommitted must be mine - the same trust level as a
      # caller-declared --own-range (todo 978). Bypasses the multi-session gate below.
      derive_notes+="  - $f: auto-derived own-range $spec (derived since $own_since, trusted - own commit history, todo 978)"$'\n'
    elif [ "$multi_session" -eq 1 ] && [ "${class_of[$f]}" != "untracked" ]; then
      unverified_files+=("$f")
      derive_notes+="  - $f: auto-derived own-range $spec, UNVERIFIED ($session_marker_count live session markers - a peer may hold lines in this file, todo 924 REOPENED)"$'\n'
    else
      derive_notes+="  - $f: auto-derived own-range $spec (every current hunk assumed own, todo 924/933)"$'\n'
    fi
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
  elif [ "${#unverified_files[@]}" -gt 0 ]; then
    # fh_rc is 0 here, meaning the check found nothing IN THE RANGES IT WAS HANDED - but for an
    # auto-derived range under multi_session that is not evidence of anything (todo 924
    # REOPENED): the check read back the exact hunk set it was given and structurally cannot
    # report a foreign hunk on that file. Never call this "clean"; it was never checked. $fh_out
    # is deliberately NOT echoed here - it holds foreign-hunk-check.sh's own per-file "clean"
    # line for these exact unverified files, and printing that text next to a refusal would be
    # the same laundering this fix exists to remove.
    if has_force foreign-hunk; then
      printf '[foreign-hunk-check] OVERRIDDEN (--force foreign-hunk): auto-derived own-range trusted despite %d live session markers for: %s\n%s\n' "$session_marker_count" "${unverified_files[*]}" "$fh_out"
    else
      printf '[foreign-hunk-check] UNVERIFIED, refusing (%d live session markers - a shared checkout means an auto-derived own-range cannot prove absence of a foreign hunk; declare --own-range for the file(s) below, or rerun with --force foreign-hunk to proceed anyway): %s\n' "$session_marker_count" "${unverified_files[*]}"
      exit 1
    fi
  else
    printf '[foreign-hunk-check] clean:\n%s\n' "$fh_out"
  fi
fi

# --- pathspec coverage check: a half-committed move leaves an add and a delete apart, and naming
# only the destination silently commits the copy while the delete rides along unreported (todo
# 495/964) - or, todo 983, never even rides along, because an archival move (complete-todo.ps1's
# raw filesystem Move-Item) never touches the index at all. That source deletion is invisible to
# `git diff --cached` (nothing was ever staged) AND falls outside the old same-directory heuristic
# (.claude/todos/<id>-*.md -> .claude/todos/done/<id>-*.md are different directories), so it needs
# both a wider read (unstaged working-tree deletions, not only staged ones) and a second match
# rule (same basename, any directory) alongside the original directory-match rule that git's own
# rename detection already fed correctly for years.
declare -A in_pathspec
for f in "${files[@]}"; do in_pathspec["$f"]=1; done
coverage_move=()
coverage_other=()
declare -A move_seen other_seen
check_coverage_hit() {
  # $1: a path NOT in the pathspec that showed up as a delete (or the old half of a rename) in
  # either diff below. Matched against $files directly, not against the diff's own "add" side -
  # an archival destination is frequently still untracked (not yet `git add`-ed when this check
  # runs), so it would never appear as an "A" in any git diff for this check to pair it against.
  #   - same directory as a pathspec file: git's own rename detection already paired an old path
  #     with a differently-named new path (e.g. src/old.txt -> src/new.txt) via R-status, so a
  #     directory match is sufficient signal there (todo 495/964's original heuristic, unchanged).
  #   - same basename as a pathspec file, regardless of directory (todo 983): the archival shape,
  #     where <id>-<slug>.md is identical on both sides and only the directory differs.
  local p="$1" pd pb d f
  [ -n "${in_pathspec[$p]:-}" ] && return
  pd=$(dirname -- "$p")
  pb=$(basename -- "$p")
  for f in "${files[@]}"; do
    d=$(dirname -- "$f")
    if [ "$d" = "$pd" ] || [ "$(basename -- "$f")" = "$pb" ]; then
      if [ -z "${move_seen[$p]:-}" ]; then
        move_seen["$p"]=1
        coverage_move+=("$p")
      fi
      return
    fi
  done
  if [ -z "${other_seen[$p]:-}" ]; then
    other_seen["$p"]=1
    coverage_other+=("$p")
  fi
}

# Staged half: `git diff --cached --name-status` - a `git mv`/`git rm`/`git add` already sitting
# in the index. Unchanged from before todo 983.
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

# Unstaged half (todo 983): `git diff --name-status` with no `--cached` diffs the index against
# the working tree, so a tracked file that a raw filesystem move deleted from disk but never
# staged (`deleted-unstaged` in classify_path above) shows up here as a plain `D` - the ONLY place
# it shows up anywhere in git, since `--cached` never saw it. Only D and the old side of an R are
# read: an untracked destination add is already known directly from $files and never appears in
# this diff at all (untracked files are invisible to `git diff` without `--others`).
unstaged=$(git_c diff --name-status)
while IFS=$'\t' read -r status path rest; do
  [ -z "$path" ] && continue
  case "$status" in
    D*) check_coverage_hit "$path" ;;
    R*) check_coverage_hit "$path" ;;
  esac
done <<<"$unstaged"

if [ "${#coverage_move[@]}" -gt 0 ]; then
  if has_force coverage; then
    printf '[coverage-check] OVERRIDDEN (--force coverage): path(s) matching the pathspec by directory or basename are not in it: %s\n' "${coverage_move[*]}"
  else
    printf '[coverage-check] REFUSED: path(s) matching the pathspec by directory or basename are not in it (possible half-committed move) - widen the pathspec, or rerun with --force coverage if deliberately leaving it behind: %s\n' "${coverage_move[*]}"
    exit 1
  fi
fi
if [ "${#coverage_other[@]}" -gt 0 ]; then
  printf '[coverage-check] warning, non-blocking (unrelated path, staged or unstaged - likely another session'"'"'s own work): %s\n' "${coverage_other[*]}"
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
