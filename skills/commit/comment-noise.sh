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

script_dir=$(cd "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$script_dir/_prefilter-lib.sh" || { printf 'ERROR: missing prefilter lib: %s/_prefilter-lib.sh\n' "$script_dir"; exit 1; }

AWK='
/^\+\+\+ b\// { f=substr($0,7); run=0; next }
/^\+/ && !/^\+\+\+/ {
  # Markdown/mdx "#" is a heading, never a comment - the cap is a code rule (todo 340).
  if (f ~ /\.(md|mdx)$/) next
  # Generated output has no author to act on a flagged block (todo 456); matched by filename
  # suffix only, never by directory, so a hand-written file under generated/ still gets checked.
  if (f ~ /\.(freezed\.dart|g\.dart|pb(enum|json|server)?\.dart|pb\.go)$/ || f ~ /_pb2\.pyi?$/ || f ~ /\.generated\.[^.\/]+$/) next
  l=substr($0,2); add[f]++
  # Bare "*" only counts as a comment continuation/close (" * text", " */") - a Rust/C deref
  # like "*state.foo = x;" has an identifier right after the star, never space/EOL/slash (779).
  # "--" is gated off for stylesheet extensions, where it is a custom-property leader
  # ("--bg: #0d0f14;"), not a comment; SQL/Lua/Haskell keep the unrestricted match (779/848).
  if (l ~ /^[[:space:]]*(\/\/|\/\*|\*([[:space:]]|$|\/)|#[^[!]|#$|<!--)/ || (f !~ /\.(css|scss|less|sass)$/ && l ~ /^[[:space:]]*--/)) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
  next
}
{ run=0 }
END {
  for (k in add) {
    ratio = (add[k]>=20 && c[k]*100/add[k]>=25)
    block = (max[k]>=5)
    if (!ratio && !block) continue
    line = sprintf("%s %d/%d (%d%%) longest %d", k, c[k], add[k], c[k]*100/add[k], max[k])
    # cut N solves 4*(c-N) < add-N so the post-trim ratio lands strictly below 25%, not merely at it.
    if (ratio) {
      cut = int((4*c[k]-add[k])/3) + 1
      line = line sprintf(" -> cut %d comment lines", cut)
    }
    if (block) {
      if (ratio) sep = ", "; else sep = " -> "
      line = line sep "longest block to 4"
    }
    print line
  }
}
'

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  printf '%s\n' "$diff_out" | awk "$AWK" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  parse_repo_arg "$@"
  set -- "${PREFILTER_ARGS[@]}"

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
  } | awk "$AWK" | sort
fi
