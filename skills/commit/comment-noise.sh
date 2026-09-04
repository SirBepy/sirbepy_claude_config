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
BEGIN {
  # haystack_file: "<file>\t<HEAD line>" pairs for every file touched by this diff, built by
  # build_haystack() below. A comment line already present at HEAD under a DIFFERENT path is a
  # verbatim move, not new authorship (todo 899) - never trimmed, so never counted as noise.
  if (haystack_file != "") {
    while ((getline hline < haystack_file) > 0) {
      sep = index(hline, "\t")
      if (sep == 0) continue
      fkey = substr(hline, 1, sep - 1)
      lkey = substr(hline, sep + 1)
      if (lkey in head_line_files) head_line_files[lkey] = head_line_files[lkey] "\001" fkey
      else head_line_files[lkey] = fkey
    }
    close(haystack_file)
  }
}
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
  if (l ~ /^[[:space:]]*(\/\/|\/\*|\*([[:space:]]|$|\/)|#[^[!]|#$|<!--)/ || (f !~ /\.(css|scss|less|sass)$/ && l ~ /^[[:space:]]*--/)) {
    moved = 0
    if (l in head_line_files) {
      n = split(head_line_files[l], parts, "\001")
      for (i = 1; i <= n; i++) if (parts[i] != f) { moved = 1; break }
    }
    # A moved line is neutral, not a run-ender: skip it without counting or resetting, so a
    # paragraph-break separator ("* ", "//") that spuriously resolves as moved (899) can no
    # longer zero out the run of a genuinely new block around it.
    if (!moved) { c[f]++; run++; if (run>max[f]) max[f]=run }
  } else run=0
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

# Every path touched by a diff, from its +++ b/ and --- a/ headers (covers a shrunk file and a
# fully deleted one alike), so a directory argument that expands past what bash can enumerate
# still yields the right file list. /dev/null (new/deleted side) is never a real path.
diff_touched_files() {
  { grep -o '^+++ b/.*' "$1" | sed 's#^+++ b/##'; grep -o '^--- a/.*' "$1" | sed 's#^--- a/##'; } \
    | grep -v '^/dev/null$' | sort -u
}

# <file>\t<HEAD line> for every line HEAD holds, across every file the diff touches - the
# pre-change content a verbatim-moved comment must already appear in somewhere else.
build_haystack() {
  local diff_file="$1" out="$2" hf hl
  : > "$out"
  diff_touched_files "$diff_file" | while IFS= read -r hf; do
    [ -z "$hf" ] && continue
    git_c show "HEAD:$hf" 2>/dev/null | while IFS= read -r hl || [ -n "$hl" ]; do
      printf '%s\t%s\n' "$hf" "$hl"
    done
  done >> "$out"
}

if [ "${1:-}" = "--range" ]; then
  diff_out=$(git diff "$2" 2>&1) || { printf 'ERROR: git diff --range %s failed: %s\n' "$2" "$diff_out"; exit 1; }
  diff_tmp=$(mktemp) && haystack_tmp=$(mktemp) || { printf 'ERROR: mktemp failed\n'; exit 1; }
  trap 'rm -f "$diff_tmp" "$haystack_tmp"' EXIT
  printf '%s\n' "$diff_out" > "$diff_tmp"
  build_haystack "$diff_tmp" "$haystack_tmp"
  awk -v haystack_file="$haystack_tmp" "$AWK" "$diff_tmp" | sort
else
  # --repo <path>: forwarded by prefilter-gate.sh when the first path argument resolves to a
  # repo other than cwd (todo 447); absent, git_c is a passthrough and behaviour is unchanged.
  parse_repo_arg "$@"
  set -- "${PREFILTER_ARGS[@]}"

  diff_tmp=$(mktemp) && haystack_tmp=$(mktemp) || { printf 'ERROR: mktemp failed\n'; exit 1; }
  trap 'rm -f "$diff_tmp" "$haystack_tmp"' EXIT

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
  } > "$diff_tmp"

  build_haystack "$diff_tmp" "$haystack_tmp"
  awk -v haystack_file="$haystack_tmp" "$AWK" "$diff_tmp" | sort
fi
