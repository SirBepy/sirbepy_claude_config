#!/usr/bin/env bash
# Em-dash prefilter: added lines only, mirrors skills/commit/secret-scan.sh's shape/exit
# convention. A pre-existing em dash on an unchanged line is not this diff's business.

# Usage: em-dash.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        em-dash.sh --range <base>        range mode (delegation-doctrine builder prefilter)

# No set -e: expected nonzero exits become a loud stdout ERROR below, never a silent
# abort, which step 5a's "no output means clean" contract would read as passing.
set -uo pipefail

# Raw bytes, never the literal character, so this file never trips its own check.
ED=$(printf '\xe2\x80\x94')
script_dir=$(cd "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$script_dir/_prefilter-lib.sh" || { printf 'ERROR: missing prefilter lib: %s/_prefilter-lib.sh\n' "$script_dir"; exit 1; }

# A todo whose SUBJECT is an em dash has to quote one, so it carries the marker defined at
# hooks/todos-em-dash-guard.py:37. Honoured here too, or such a file stays writable but
# permanently uncommittable (todo 778). Scoped to .claude/todos/, exactly as that guard is.
EXEMPT_MARKER='<!-- em-dash-exempt -->'
exempt_list() {
  local f p key
  for f in "$@"; do
    case "$f" in *".claude/todos/"*) ;; *) continue ;; esac
    case "$f" in /*|?:[/\\]*) p="$f" ;; *) p="${repo:+$repo/}$f" ;; esac
    [ -f "$p" ] || continue
    grep -qF -- "$EXEMPT_MARKER" "$p" 2>/dev/null || continue
    # Diff headers are always repo-relative for a tracked or discovered-untracked file;
    # only a gitignored file (invisible to ls-files) keeps the argument's own form.
    key=$(git_c ls-files --full-name -- "$f" 2>/dev/null)
    [ -z "$key" ] && key=$(git_c ls-files --others --exclude-standard --full-name -- "$f" 2>/dev/null)
    printf '%s\n' "${key:-$f}"
  done
}

# is_binary_path()/binary_list(): shared with secret-scan.sh via
# _prefilter-lib.sh, so both prefilters agree on which files are binary.

AWK='
BEGIN { while ((getline row < EXEMPTFILE) > 0) if (row != "") ex[row]=1; close(EXEMPTFILE) }
/^diff --git / { f="?"; skip=0; next }
/^\+\+\+ b\// { f=substr($0,7); skip=(f in ex); next }
/^@@/ { match($0, /\+[0-9]+/); ln=substr($0, RSTART+1, RLENGTH-1)+0; next }
/^\+/ && !/^\+\+\+/ { l=substr($0,2); if (!skip && index(l, ED) > 0) printf "%s:%d\n", f, ln; ln++; next }
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git_c diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  changed=(); while IFS= read -r n; do [ -n "$n" ] && changed+=("$n"); done < <(git_c diff --name-only "$2" 2>/dev/null)
  exempt=$(printf '%s\n%s' "$(exempt_list ${changed+"${changed[@]}"})" "$(binary_list ${changed+"${changed[@]}"})")
  exempt_file=$(write_exempt_file "$exempt")
  printf '%s\n' "$diff_out" | awk -v ED="$ED" -v EXEMPTFILE="$exempt_file" "$AWK" | sort
  rm -f "$exempt_file"
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  parse_repo_arg "$@"
  set -- "${PREFILTER_ARGS[@]}"
  exempt=$(printf '%s\n%s' "$(exempt_list "$@")" "$(binary_list "$@")")
  exempt_file=$(write_exempt_file "$exempt")

  {
    git_c_paths diff HEAD -- "$@"
    # untracked_diffs lists the files NUL-separated (ls-files -z): git status quotes space-
    # containing names, which broke the downstream git diff --no-index call.
    untracked_diffs "$@"
    scan_invisible_paths "$@"
  } | awk -v ED="$ED" -v EXEMPTFILE="$exempt_file" "$AWK" | sort
  rm -f "$exempt_file"
fi
