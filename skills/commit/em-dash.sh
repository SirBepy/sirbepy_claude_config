#!/usr/bin/env bash
# Em-dash prefilter: added lines only, mirrors skills/commit/comment-noise.sh's shape/exit
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

# A text-heavy binary (PDF, font) can clear 8KB with no NUL byte, so git's own `+++ /dev/null`
# vs real-diff heuristic (used below for untracked files) still emits it as scannable text
# (todo 986). Extension is checked first since that is the exact shape that slipped through;
# the NUL sniff backs it up for an extensionless binary.
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

# Routes a binary path into the AWK scanner's existing skip set rather than reshaping the
# diff-gathering calls below - they already key "skip" off the '+++ b/<key>' header, so
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

AWK='
BEGIN { n=split(EXEMPT, e, "\n"); for (i=1; i<=n; i++) if (e[i] != "") ex[e[i]]=1 }
/^\+\+\+ b\// { f=substr($0,7); skip=(f in ex); next }
/^@@/ { match($0, /\+[0-9]+/); ln=substr($0, RSTART+1, RLENGTH-1)+0; next }
/^\+/ && !/^\+\+\+/ { l=substr($0,2); if (!skip && index(l, ED) > 0) printf "%s:%d\n", f, ln; ln++; next }
/^-/ { next }
{ ln++ }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  changed=(); while IFS= read -r n; do [ -n "$n" ] && changed+=("$n"); done < <(git diff --name-only "$2" 2>/dev/null)
  exempt=$(printf '%s\n%s' "$(exempt_list ${changed+"${changed[@]}"})" "$(binary_list ${changed+"${changed[@]}"})")
  printf '%s\n' "$diff_out" | awk -v ED="$ED" -v EXEMPT="$exempt" "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  parse_repo_arg "$@"
  set -- "${PREFILTER_ARGS[@]}"
  exempt=$(printf '%s\n%s' "$(exempt_list "$@")" "$(binary_list "$@")")

  {
    git_c diff HEAD -- "$@"
    # -z/NUL-separated: git status quotes space-containing names, which broke the downstream
    # git diff --no-index call; ls-files -z sidesteps quoting entirely.
    git_c ls-files --others --exclude-standard -z -- "$@" | while IFS= read -r -d '' f; do
      out=$(git_c diff --no-index -- /dev/null "$f" 2>&1); rc=$?
      if [ "$rc" -gt 1 ]; then
        printf 'ERROR: could not inspect untracked file %s (git diff --no-index exit %d): %s\n' "$f" "$rc" "$out"
      else
        printf '%s\n' "$out"
      fi
    done
    scan_invisible_paths "$@"
  } | awk -v ED="$ED" -v EXEMPT="$exempt" "$AWK" | sort
fi
