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
#     [--force <check>[,<check>...]] [--todo <id>]... -m <message> [-m <body>]... -- <file> [<file> ...]
#
# --todo <id> (repeatable, todo 1105): appends that todo's archive-move paths to the pathspec
# itself, so a caller closing a backlog item names the id once instead of hand-globbing
# complete-todo.ps1's own output - `.claude/todos/done/<id>-*.md` when that file exists on disk,
# and `.claude/todos/<id>-*.md` when git still tracks it (an untracked, peer-filed todo has no
# source half to name, so only the done/ file is added). `--` may be given with zero explicit
# files when --todo alone supplies the whole pathspec.
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
# --force values: head-guard, overlap, foreign-hunk, coverage, coverage-tests. Never: branch-guard,
# prefilter.
#
# Exit 0: committed, full sha printed on the last line. Exit 1: a check refused (nothing
# committed) - the printed verdict says what to decide. Exit 2: could not run (bad args/repo/git
# failure) - not a finding to act on, fix and rerun.
set -uo pipefail

# Suppresses only the "LF will be replaced by CRLF" / "CRLF will be replaced by LF" class of
# warning (todo 1115): core.safecrlf's default "warn" still runs the same conversion, it just
# prints first - every diff this script or a child script (prefilter-gate.sh and whatever it
# forwards to) takes against a tracked file re-triggers it once per file in an autocrlf repo,
# flooding real output and tempting a caller into a forbidden pipe/filter to read past it.
# core.safecrlf=false never turns a prior success into a failure (unlike =true, which can),
# so this cannot change any exit code - only the warning text disappears. Exported as GIT_CONFIG_*
# rather than a per-call `-c` flag so a child bash script's OWN git calls (em-dash.sh, secret-
# scan.sh, comment-tense.sh, comment-noise.sh - none of which this script owns or invokes via
# `git -c`) inherit the same suppression through the environment.
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=core.safecrlf
export GIT_CONFIG_VALUE_0=false

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

repo_in=""
expect_branch=""
expect_sha=""
own_shas=""
own_since=""
declare -A explicit_ranges
force_list=""
messages=()
todo_ids=()
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
    # Appended, not assigned (todo 1053): a repeated --force flag is how a caller naturally
    # writes "override these two checks", and an assignment here silently dropped every
    # earlier one, honouring only the last --force actually typed.
    --force) force_list="${force_list:+$force_list,}${2:-}"; shift 2 ;;
    # Appended, not assigned (todo 1109): a repeated -m is the natural way to pass a subject
    # plus body paragraphs, the way `git commit -m A -m B` does - an assignment here silently
    # dropped every -m but the last, landing the BODY text as the commit's subject line.
    -m|--message) messages+=("${2:-}"); shift 2 ;;
    --todo) todo_ids+=("${2:-}"); shift 2 ;;
    --) shift; files=("$@"); break ;;
    *) printf 'ERROR: unknown argument %s\n' "$1"; exit 2 ;;
  esac
done

# The files-non-empty half of this check runs further down (after --todo resolution): a
# --todo-only call legitimately has zero explicit files at parse time, filling the pathspec
# entirely from the ids' own archive paths.
if [ -z "$expect_branch" ] || [ -z "$expect_sha" ] || [ "${#messages[@]}" -eq 0 ]; then
  printf 'ERROR: --expect-branch, --expect-sha and -m are all required\n'
  exit 2
fi

# --- AI attribution refusal - checked first, before the prefilter gate or any repo
# work, so a refusal is cheap; never overridable, matching /commit SKILL.md's "never add
# Co-authored-by: Claude or any AI attribution" with no exception. A trailer line is matched
# case-insensitively at the start of a line so a prose mention ("FIX: Player Claude listener")
# never matches; the "generated with" line has no anchor since that phrase is never legitimate
# mid-sentence prose.
for m in "${messages[@]}"; do
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    if printf '%s' "$line" | grep -qiE '^co-authored-by:.*(claude|anthropic)'; then
      printf 'REFUSED: commit message carries an AI attribution trailer, never allowed - matched line: %s\n' "$line"
      exit 1
    fi
    if printf '%s' "$line" | grep -qiE 'generated with \[?claude code'; then
      printf 'REFUSED: commit message carries an AI attribution line, never allowed - matched line: %s\n' "$line"
      exit 1
    fi
  done <<<"$m"
done

if [ -n "$force_list" ]; then
  IFS=',' read -r -a force_arr <<<"$force_list"
  normalized_force=()
  for c in "${force_arr[@]}"; do
    # overlap-check is accepted as an alias for overlap (todo 1076): it is the exact label
    # the overlap-check REFUSED message itself prints, and typing that back verbatim was the
    # second failed call the todo measured.
    [ "$c" = "overlap-check" ] && c=overlap
    case "$c" in
      head-guard|overlap|foreign-hunk|coverage|coverage-tests) normalized_force+=("$c") ;;
      branch-guard|prefilter|prefilter-gate)
        printf 'ERROR: --force %s is never accepted - branch-guard and the prefilter gate are not overridable\n' "$c"
        exit 2 ;;
      *)
        printf 'ERROR: unknown --force check name %s (valid: head-guard, overlap, foreign-hunk, coverage, coverage-tests)\n' "$c"
        exit 2 ;;
    esac
  done
  force_list=$(IFS=,; echo "${normalized_force[*]}")
fi
has_force() { [[ ",$force_list," == *",$1,"* ]]; }

repo_check="${repo_in:-.}"
if ! git -C "$repo_check" rev-parse --show-toplevel >/dev/null 2>&1; then
  printf 'ERROR: %s is not a git repository\n' "$repo_check"
  exit 2
fi
repo_root=$(git -C "$repo_check" rev-parse --show-toplevel)
git_c() { git -C "$repo_root" "$@"; }

# --todo <id> resolution (todo 1105): the done/ half is a filesystem glob (complete-todo.ps1's
# Move-Item never touches the index, so the file is untracked new content, not a git object yet)
# and the source half is a git pathspec glob gated on still being tracked - an untracked source
# (a peer-filed todo that was never committed) has no deletion for this commit to carry, and
# `git ls-files` on it correctly returns nothing rather than a path to add.
declare -A todo_seen
for f in "${files[@]}"; do todo_seen["$f"]=1; done
for tid in "${todo_ids[@]}"; do
  shopt -s nullglob
  for donef in "$repo_root"/.claude/todos/done/"$tid"-*.md; do
    [ -e "$donef" ] || continue
    rel="${donef#"$repo_root"/}"
    if [ -z "${todo_seen[$rel]:-}" ]; then
      todo_seen["$rel"]=1
      files+=("$rel")
    fi
  done
  shopt -u nullglob
  while IFS= read -r -d '' trackedf; do
    [ -z "$trackedf" ] && continue
    if [ -z "${todo_seen[$trackedf]:-}" ]; then
      todo_seen["$trackedf"]=1
      files+=("$trackedf")
    fi
  done < <(git_c ls-files -z -- ".claude/todos/${tid}-*.md" 2>/dev/null)
done

if [ "${#files[@]}" -eq 0 ]; then
  printf 'ERROR: -- <files> or --todo <id> must supply at least one path\n'
  exit 2
fi

# --expect-sha accepts a short sha (todo 994): resolve it against this repo before the
# head-guard comparison, the same normalization a caller would otherwise have to do by hand.
# Restricted to a bare hex string so a branch/tag name typo can never silently resolve to
# today's HEAD and defeat the guard it is supposed to be.
if [[ "$expect_sha" =~ ^[0-9a-fA-F]{4,40}$ ]]; then
  resolved_expect_sha=$(git_c rev-parse --verify "$expect_sha" 2>/dev/null) || resolved_expect_sha=""
  [ -n "$resolved_expect_sha" ] && expect_sha="$resolved_expect_sha"
fi

# Defers to the single client-repo source of truth: refs/client-repos.txt, read through
# hooks/_client_repo.py, the same list snippets/client-repo.md and the Pre-push gate already key
# off. "personal" (not on the list, whoever owns it, including no remote at all) is personal;
# anything else - "client", or the script failing to run at all (no python on PATH, a bad path) -
# is treated as client, the stricter refusing direction, so a broken check can never silently
# open the never-ask branch below.
is_personal_repo() {
  local out rc
  out=$(python "$dir/../../hooks/_client_repo.py" is-client "$repo_root" 2>/dev/null); rc=$?
  [ "$rc" -eq 0 ] && [ "$out" = "personal" ]
}

# A path's exemption from the multi-session gate below keys on "no blob at HEAD", not on
# classify_path's live/untracked split (todo 1026): a file the caller already `git add`-ed
# before calling this script is "live" per classify_path (it is in the index now), but if it
# was never part of any commit it still has no HEAD baseline for a peer's lines to hide
# inside - the exact case the untracked exemption exists for.
file_has_head_blob() { git_c cat-file -e "HEAD:$1" 2>/dev/null; }

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

# Prints every hunk header plus its first changed line for one file - the per-hunk visibility a
# bare `--force foreign-hunk` never gave before taking an auto-derived range on trust. "First
# changed line" is the first +/- content line after a `@@` marker; the +++/--- file headers never
# reach here since they sit before the first `@@`.
print_taken_hunks() {
  local f="$1" diff="$2" line header="" first_line="" out=""
  while IFS= read -r line; do
    if [[ "$line" == '@@ '* ]]; then
      if [ -n "$header" ]; then
        out+="  - $f: $header"$'\n'
        [ -n "$first_line" ] && out+="    $first_line"$'\n'
      fi
      header="$line"
      first_line=""
      continue
    fi
    if [ -n "$header" ] && [ -z "$first_line" ] && { [[ "$line" == '+'* ]] || [[ "$line" == '-'* ]]; }; then
      first_line="$line"
    fi
  done <<<"$diff"
  if [ -n "$header" ]; then
    out+="  - $f: $header"$'\n'
    [ -n "$first_line" ] && out+="    $first_line"$'\n'
  fi
  printf '%s' "$out"
}

# live/untracked/deleted-staged/deleted-unstaged/unknown. Neither overlap-check.sh nor
# foreign-hunk-check.sh understands a deleted path (both crash or misreport on one, the second
# defect this script exists to remove) - deleted-staged and deleted-unstaged both leave nothing
# in the working tree to diff, whether the deletion was ever `git rm`'d or not (todo 1033 item
# 2), so both are excluded from both checks' file lists below but still reach the commit pathspec.
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
  [ "$c" != "deleted-staged" ] && [ "$c" != "deleted-unstaged" ] && diffable_files+=("$f")
done

# Directory pathspec expansion (todo 1101): an already-tracked directory entry (classified
# "live" above, since `git ls-files --error-unmatch` matched at least one tracked path inside
# it) still leaves a brand-new file in that directory as a plain untracked path that
# `git commit -- <dir>` never adds - git's own pathspec match follows tracked content only, so
# the file stayed `??` while the script printed "[commit] committed". List every untracked file
# under the directory and treat each one exactly like a named new file from here on: classified,
# diffed, staged and committed alongside it. A wholly-untracked directory entry is already
# classified "untracked" above and `git add -- <dir>` already recurses into it on its own, so it
# is skipped here to avoid double-processing the same files under a second code path.
for f in "${files[@]}"; do
  [ "${class_of[$f]}" = "live" ] || continue
  [ -d "$repo_root/$f" ] || continue
  # -z plus quotePath off: a default listing C-quotes non-ASCII names ("d/\304\215vor.txt"),
  # which then cannot be staged and aborts the whole commit.
  while IFS= read -r -d '' newf; do
    [ -z "$newf" ] && continue
    [ -n "${class_of[$newf]:-}" ] && continue
    class_of["$newf"]=untracked
    files+=("$newf")
    diffable_files+=("$newf")
  done < <(git_c -c core.quotePath=false ls-files -z --others --exclude-standard -- "$f")
done

echo "=== commit-pathspec: $repo_root ==="
printf '[pathspec] classification:\n'
for f in "${files[@]}"; do
  note=""
  { [ "${class_of[$f]}" = "deleted-staged" ] || [ "${class_of[$f]}" = "deleted-unstaged" ]; } && note=" (excluded from overlap-check/foreign-hunk-check - nothing left to diff)"
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
    elif is_personal_repo; then
      # SKILL.md step 8, "On exit 1, evaluate in this order" branch 2: a personal repo has no
      # cross-ticket boundary to cross, so Claude never asks on an overlap hit there and always
      # takes the genuinely-separate-work branch (todo 1076) - this proceeds the same way
      # instead of making every personal-repo commit pay for a --force round trip.
      printf '[overlap-check] info, personal repo: proceeding (SKILL.md step 8 branch 2):\n%s\n' "$ov_out"
    else
      printf '[overlap-check] REFUSED (judgement call - see SKILL.md step 8, "On exit 1, evaluate in this order"; rerun with --force overlap to proceed anyway):\n%s\n' "$ov_out"
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
# A live marker elsewhere on the machine says nothing about THIS repo (todo 985): the marker
# is keyed by session id, not by repo, so "4 live session markers" routinely meant 4 sessions
# in 4 unrelated repos, refusing a solo-repo commit as reflexively as a genuinely shared one.
# Resolve each marker's session to its registered cwd via ~/.claude/sessions/*.json - the same
# sessionId/cwd pair write-session-marker.ps1 itself reads for pid liveness - and count only
# the ones whose cwd is this repo or a path under it.
session_registry_dir="${COMMIT_PATHSPEC_SESSION_REGISTRY_DIR:-$dir/../../sessions}"
marker_shares_this_repo() {
  # No resolvable record (missing registry, unparseable line, no matching sessionId) stays
  # counted as sharing this repo - unresolved inflates the count rather than clearing it, the
  # same safe-direction rule the comment above this block already commits to for stale
  # markers: never let missing data make a genuinely shared tree look solo.
  local session_id="$1" f line cwd norm_cwd norm_repo
  norm_repo=$(printf '%s' "$repo_root" | tr '[:upper:]' '[:lower:]')
  norm_repo="${norm_repo%/}"
  [ -d "$session_registry_dir" ] || return 0
  shopt -s nullglob
  for f in "$session_registry_dir"/*.json; do
    line=$(grep -F "\"sessionId\":\"$session_id\"" "$f" 2>/dev/null) || continue
    cwd=$(printf '%s' "$line" | grep -oE '"cwd":"[^"]*"')
    cwd="${cwd#*:\"}"; cwd="${cwd%\"}"
    cwd=$(printf '%s' "$cwd" | sed 's/\\\\/\//g')
    norm_cwd=$(printf '%s' "$cwd" | tr '[:upper:]' '[:lower:]')
    norm_cwd="${norm_cwd%/}"
    shopt -u nullglob
    case "$norm_cwd" in
      "$norm_repo"|"$norm_repo"/*) return 0 ;;
      *) return 1 ;;
    esac
  done
  shopt -u nullglob
  return 0
}
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
        if marker_shares_this_repo "${marker_path##*/}"; then
          session_marker_count=$((session_marker_count + 1))
        fi ;;
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
declare -A unverified_diff
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
    if [ -n "$own_since" ] && file_has_head_blob "$f"; then
      # Traces to a concrete, git-verifiable commit list (own_since..HEAD), not an assumption
      # that whatever is currently uncommitted must be mine - the same trust level as a
      # caller-declared --own-range (todo 978). Bypasses the multi-session gate below.
      derive_notes+="  - $f: auto-derived own-range $spec (derived since $own_since, trusted - own commit history, todo 978)"$'\n'
    elif [ "$multi_session" -eq 1 ] && file_has_head_blob "$f"; then
      unverified_files+=("$f")
      unverified_diff["$f"]="$diff_out"
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
      # A bare --force foreign-hunk used to take a peer's in-progress lines whole, with no
      # warning, because the override trusted an auto-derived range exactly as blindly as the
      # UNVERIFIED verdict it was overriding. A file with 2+ hunks and no caller --own-range is
      # refused even under --force foreign-hunk - the override needs a stated claim (--own-range
      # per hunk) rather than a bare flag. A single-hunk file has nothing left to disambiguate (one
      # hunk is the whole candidate), so it proceeds, but every hunk it is about to take is printed
      # first via print_taken_hunks - the visibility the 2026-10-07 incident had none of.
      needs_range=()
      hunk_notes=""
      for uf in "${unverified_files[@]}"; do
        hunk_count=$(printf '%s\n' "${unverified_diff[$uf]}" | grep -c '^@@ ')
        if [ "$hunk_count" -ge 2 ]; then
          needs_range+=("$uf")
        else
          # Command substitution strips the trailing newline print_taken_hunks always emits
          # (bash's own $(...) rule, not a print_taken_hunks defect) - re-add it so a second
          # file's block does not run on to the end of this one's line.
          hunk_notes+="$(print_taken_hunks "$uf" "${unverified_diff[$uf]}")"$'\n'
        fi
      done
      if [ "${#needs_range[@]}" -gt 0 ]; then
        printf '[foreign-hunk-check] REFUSED despite --force foreign-hunk (%d live session markers): file(s) below have 2+ auto-derived hunks with no caller --own-range - a bare --force cannot take a multi-hunk file sight-unseen, declare --own-range for each hunk you actually own and rerun: %s\n' "$session_marker_count" "${needs_range[*]}"
        exit 1
      fi
      printf '[foreign-hunk-check] OVERRIDDEN (--force foreign-hunk): auto-derived own-range trusted despite %d live session markers for: %s\n' "$session_marker_count" "${unverified_files[*]}"
      printf '[foreign-hunk-check] hunk(s) taken on trust:\n%s' "$hunk_notes"
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
  # $1: a path NOT in the pathspec that showed up in either diff below. $2: 1 when $1's status
  # is deletion-shaped (a plain delete, or the old side of a rename) - 0 for anything else
  # (add, modify, the new side of a rename), i.e. the path still fully exists somewhere and so
  # cannot be "half of a move" (todo 1073).
  #   - same directory as a pathspec file: git's own rename detection already paired an old path
  #     with a differently-named new path (e.g. src/old.txt -> src/new.txt) via R-status, so a
  #     directory match is sufficient signal there (todo 495/964's original heuristic, unchanged
  #     for any status - an unrelated ADD or MODIFY co-located with the pathspec was already the
  #     documented "move shape" per SKILL.md step 8, not something this todo revisits).
  #   - same basename as a pathspec file, regardless of directory (todo 983): the archival shape,
  #     where <id>-<slug>.md is identical on both sides and only the directory differs. Gated on
  #     $2 (todo 1073): a same-basename file elsewhere that is merely being edited, not deleted
  #     or renamed away, is not missing anything a move would have left behind - the false
  #     positive was this basename rule firing on a staged MODIFY to an unrelated file that
  #     happened to share a filename with the pathspec's own target. ALSO gated on the pathspec
  #     file having no HEAD blob (coverage-basename-new-file): a move's destination is always
  #     new, but an EXISTING pathspec file that is merely being edited already had its own HEAD
  #     blob before this commit touched it, so an unrelated deletion sharing its basename is not
  #     "half of a move" either - without this, editing skills/foo/SKILL.md while an unrelated
  #     skills/bar/SKILL.md deletion was pending anywhere else refused on basename alone.
  local p="$1" is_del="$2" pd pb d f fn
  [ -n "${in_pathspec[$p]:-}" ] && return
  # Directory-pathspec containment: a path equal to, or nested at any depth under,
  # a pathspec entry that is ITSELF a directory is already covered the way `git commit -- <dir>`
  # covers it natively - this is a stronger, exact membership test, not the same-directory-level
  # heuristic below (which only ever compares two paths' immediate dirname, so it can never match
  # a directory pathspec entry against a file nested two or more levels under it). Backslashes are
  # normalized and a trailing slash stripped first, matching how a caller might type a Windows-
  # style or slash-terminated directory pathspec; $p itself never needs this since it always comes
  # from git's own output, which is already forward-slash. Gated on -d so a FILE pathspec entry
  # (e.g. src/new.txt) never falls into this branch and still reaches the heuristic below.
  for f in "${files[@]}"; do
    fn="${f//\\//}"
    fn="${fn%/}"
    [ -d "$repo_root/$fn" ] || continue
    case "$p" in
      "$fn"|"$fn"/*) return ;;
    esac
  done
  pd=$(dirname -- "$p")
  pb=$(basename -- "$p")
  for f in "${files[@]}"; do
    d=$(dirname -- "$f")
    if [ "$d" = "$pd" ] || { [ "$is_del" = "1" ] && [ "$(basename -- "$f")" = "$pb" ] && ! file_has_head_blob "$f"; }; then
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
# in the index. Every staged status still reaches check_coverage_hit, unchanged from before
# todo 983 - only the is_del flag it is passed is new.
staged=$(git_c diff --cached --name-status)
while IFS=$'\t' read -r status path rest; do
  [ -z "$path" ] && continue
  if [[ "$status" == R* ]]; then
    check_coverage_hit "$path" 1
    check_coverage_hit "$rest" 0
  else
    is_del=0
    [[ "$status" == D* ]] && is_del=1
    check_coverage_hit "$path" "$is_del"
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
    D*) check_coverage_hit "$path" 1 ;;
    R*) check_coverage_hit "$path" 1; check_coverage_hit "$rest" 0 ;;
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

# --- test-coverage check: SKILL.md step 6b's "pathspec changes non-test source files and
# touches no test file" rule, mechanised instead of applied by eye per commit.
# Deleted paths count as changed - $files already holds them (classify_path above), and removing
# a source file untested is the same unverified-change shape as editing one.
# Deliberately narrower than hooks/_testing_floor_lib.py's SOURCE_SUFFIXES: that list decides what
# is worth a fast-check run, this one what must ship with a test file, and stylesheets, SQL,
# C++ headers and Gradle scripts rarely get a test file of their own.
is_source_file() {
  case "$1" in
    .claude/todos/*|*/.claude/todos/*) return 1 ;;
  esac
  case "$1" in
    *.py|*.js|*.mjs|*.cjs|*.ts|*.tsx|*.jsx|*.dart|*.rs|*.go|*.rb|*.java|*.kt|*.swift|*.c|*.cc|*.cpp|*.h|*.cs|*.php|*.lua|*.luau|*.sh|*.ps1|*.vue|*.svelte) return 0 ;;
    *) return 1 ;;
  esac
}
is_test_path() {
  local base
  base=$(basename -- "$1")
  case "$base" in
    test_*|*_test.*|*.test.*|*.spec.*) return 0 ;;
  esac
  case "/$1/" in
    */test/*|*/tests/*|*/__tests__/*|*/spec/*) return 0 ;;
  esac
  return 1
}
has_source=0
has_test=0
for f in "${files[@]}"; do
  is_test_path "$f" && has_test=1
  is_source_file "$f" && has_source=1
done
if [ "$has_source" -eq 1 ] && [ "$has_test" -eq 0 ]; then
  if has_force coverage-tests; then
    printf '[coverage-tests-check] OVERRIDDEN (--force coverage-tests): pathspec changes non-test source file(s) and touches no test file\n'
  else
    printf '[coverage-tests-check] REFUSED: pathspec changes non-test source file(s) and touches no test file - write the test that fails without this change, or rerun with --force coverage-tests if the change is untestable: %s\n' "${files[*]}"
    exit 1
  fi
else
  printf '[coverage-tests-check] clean\n'
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
# Each -m lands as its own paragraph (git joins them with a blank line), matching
# `git commit -m A -m B`'s own subject+body shape - todo 1109.
commit_msg_args=()
for m in "${messages[@]}"; do commit_msg_args+=(-m "$m"); done
if ! commit_out=$(git_c commit "${commit_msg_args[@]}" -- "${files[@]}" 2>&1); then
  printf '[commit] ERROR: git commit failed:\n%s\n' "$commit_out"
  exit 2
fi
printf '[commit] committed\n'
git_c rev-parse HEAD
