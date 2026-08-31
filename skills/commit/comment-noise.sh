#!/usr/bin/env bash
# Comment-noise prefilter; the cap itself is defined in skills/commit/comment-noise.md.
# On disk rather than markdown-embedded: skill-argument substitution rewrites a bare $0 in a
# skill body, which clobbered awk's $0 ("whole current line") every time this was pasted inline.

# Usage: comment-noise.sh <file> [<file> ...]   working-tree mode (/commit step 5a)
#        comment-noise.sh --range <base>        range mode (/create-pr step 2, branch diff)
# No set -e: expected nonzero exits (git diff --no-index differs, bad --range sha) are handled
# explicitly below and turned into a loud stdout ERROR line, never a silent abort that reads as
# "no output means clean" per step 5a's contract.
set -uo pipefail

AWK='
/^\+\+\+ b\// { f=substr($0,7); run=0; next }
/^\+/ && !/^\+\+\+/ {
  # Markdown/mdx "#" is a heading, never a comment - the cap is a code rule (todo 340).
  if (f ~ /\.(md|mdx)$/) next
  # Generated output has no author to act on a flagged block (todo 456); matched by filename
  # suffix only, never by directory, so a hand-written file under generated/ still gets checked.
  if (f ~ /\.(freezed\.dart|g\.dart|pb(enum|json|server)?\.dart|pb\.go)$/ || f ~ /_pb2\.pyi?$/ || f ~ /\.generated\.[^.\/]+$/) next
  l=substr($0,2); add[f]++
  if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
  next
}
{ run=0 }
END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  repo=""
  if [ "${1:-}" = "--repo" ]; then repo="$2"; shift 2; fi
  git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }

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
  } | awk "$AWK" | sort
fi
