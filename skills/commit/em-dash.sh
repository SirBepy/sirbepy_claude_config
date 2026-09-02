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
repo=""
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

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
  exempt=$(exempt_list ${changed+"${changed[@]}"})
  printf '%s\n' "$diff_out" | awk -v ED="$ED" -v EXEMPT="$exempt" "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  if [ "${1:-}" = "--repo" ]; then repo="$2"; shift 2; fi
  exempt=$(exempt_list "$@")

  # A path git cannot see (gitignored, or missing) yields no diff below, which reads as
  # "clean" though nothing was seen (todo 460). Scan it via --no-index like an untracked
  # file instead, since the caller named it on purpose.
  invisible=()
  for a in "$@"; do
    if git_c ls-files --error-unmatch -- "$a" >/dev/null 2>&1; then continue; fi
    if [ -n "$(git_c ls-files --others --exclude-standard -- "$a")" ]; then continue; fi
    invisible+=("$a")
  done

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
    if [ "${#invisible[@]}" -gt 0 ]; then
      for f in "${invisible[@]}"; do
        out=$(git_c diff --no-index -- /dev/null "$f" 2>&1); rc=$?
        if [ "$rc" -gt 1 ]; then
          printf 'ERROR: could not inspect invisible file %s (git diff --no-index exit %d): %s\n' "$f" "$rc" "$out"
        else
          printf '%s\n' "$out"
        fi
      done
    fi
  } | awk -v ED="$ED" -v EXEMPT="$exempt" "$AWK" | sort
fi
