#!/usr/bin/env bash
# Fixture suite for secret-scan.sh, comment-noise.sh, em-dash.sh, overlap-check.sh (todo 810),
# foreign-hunk-check.sh (todos 1033, 1064), seeded from done/412, done/460, done/456, done/778.
# Invoke directly:
#   bash skills/commit/test_prefilters.sh
# The comment-noise.sh cut-ratio arithmetic (the exact-25%-boundary math) has no test coverage
# here: its old suite, test_comment_noise.sh, was deleted with the cap it tested (todo 922).
# Accepted gap - the number is advisory-only now, not a gate; see todo 935.
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
gate="$script_dir/prefilter-gate.sh"
secret_scan="$script_dir/secret-scan.sh"
comment_noise="$script_dir/comment-noise.sh"
em_dash="$script_dir/em-dash.sh"
overlap_check="$script_dir/overlap-check.sh"
foreign_hunk_check="$script_dir/foreign-hunk-check.sh"

fail=0
tmp_dirs=()
cleanup() { for d in "${tmp_dirs[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

new_repo() {
  local d
  d=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
  # Every caller runs this via `x=$(new_repo)`, a subshell whose own tmp_dirs append never
  # reaches the parent's array - the caller must register $d itself, right after this returns.
  git -C "$d" init -q
  git -C "$d" config user.email "test@example.com"
  git -C "$d" config user.name "test"
  # Deterministic hunks: autocrlf would turn every line into a line-ending change too, widening
  # every diff hunk to the whole file and breaking exact-range assertions below.
  git -C "$d" config core.autocrlf false
  printf 'seed\n' > "$d/README.md"
  git -C "$d" add README.md
  git -C "$d" commit -q -m seed
  printf '%s' "$d"
}

check() {
  local desc=$1 want_exit=$2 want_pattern=$3 unwant_pattern=$4 out=$5 got_exit=$6
  if [ "$got_exit" != "$want_exit" ]; then
    echo "FAIL: $desc - exit $got_exit, want $want_exit (out: $out)"
    fail=1
    return
  fi
  if [ -n "$want_pattern" ] && ! printf '%s' "$out" | grep -qE "$want_pattern"; then
    echo "FAIL: $desc - output missing /$want_pattern/: $out"
    fail=1
    return
  fi
  if [ -n "$unwant_pattern" ] && printf '%s' "$out" | grep -qE "$unwant_pattern"; then
    echo "FAIL: $desc - output unexpectedly matched /$unwant_pattern/: $out"
    fail=1
    return
  fi
  echo "PASS: $desc"
}

# --- secret-scan.sh: blind inside a foreign git root (done/412) ---
# A separate repo nested in the parent's working tree reproduces the gate's per-path
# repo-grouping without needing a real `git submodule add`; the bug was root resolution, not
# the gitlink record.
parent=$(new_repo); tmp_dirs+=("$parent")
mkdir -p "$parent/vendor/sub"
git -C "$parent/vendor/sub" init -q
git -C "$parent/vendor/sub" config user.email "test@example.com"
git -C "$parent/vendor/sub" config user.name "test"
printf 'seed\n' > "$parent/vendor/sub/README.md"
git -C "$parent/vendor/sub" add README.md
git -C "$parent/vendor/sub" commit -q -m seed
# Built from two halves so this script's OWN source line never contains the contiguous
# token shape secret-scan.sh looks for and flags itself.
fake_tok="ghp_""abcdefghij1234567890abcdef"
printf 'const tok = "%s";\n' "$fake_tok" > "$parent/vendor/sub/config.js"
out=$(cd "$parent" && "$gate" vendor/sub/config.js); rc=$?
check "secret-scan.sh sees a planted credential inside a foreign repo root" \
  1 'config\.js:1: ghp_' '' "$out" "$rc"

# --- secret-scan.sh: blind on a gitignored path (done/460) ---
repo=$(new_repo); tmp_dirs+=("$repo")
printf '*\n' > "$repo/.gitignore"
fake_tok2="ghp_""zyxwvutsrqponmlkjihgfed"
printf 'const tok = "%s";\n' "$fake_tok2" > "$repo/secrets.txt"
out=$(cd "$repo" && "$gate" secrets.txt); rc=$?
check "secret-scan.sh sees a planted credential in a gitignored file" \
  1 'secrets\.txt:1: ghp_' '' "$out" "$rc"

printf 'nothing to see here\n' > "$repo/clean.txt"
out=$(cd "$repo" && "$gate" clean.txt); rc=$?
check "an unremarkable gitignored file still clears the gate" 0 '' '' "$out" "$rc"

# --- prefilter-gate.sh: staged deletion is skipped, not a repo-resolution failure (todo 944) ---
# git rm'ing the only file in a directory removes the directory too, so the deleted path's own
# dirname is gone from disk - the exact shape that made repo resolution exit 2 in the wild.
delrepo=$(new_repo); tmp_dirs+=("$delrepo")
mkdir -p "$delrepo/assets"
printf 'seed\n' > "$delrepo/assets/README.md"
git -C "$delrepo" add assets/README.md
git -C "$delrepo" commit -q -m "add assets/README.md"
git -C "$delrepo" rm -q assets/README.md
out=$(cd "$delrepo" && "$gate" assets/README.md); rc=$?
check "a lone staged deletion whose own directory is gone clears the gate instead of exit 2" \
  0 '' 'ERROR' "$out" "$rc"

# A staged deletion mixed into a pathspec with a live file must not blind the scan of that
# live file - the whole point of skipping rather than aborting is the rest keeps getting checked.
printf 'seed\n' > "$delrepo/keep.txt"
git -C "$delrepo" add keep.txt
git -C "$delrepo" commit -q -m "add keep.txt"
fake_tok3="ghp_""lmnopqrstuvwxyzabcdefghi"
printf 'seed\nconst tok = "%s";\n' "$fake_tok3" > "$delrepo/keep.txt"
git -C "$delrepo" rm -q README.md
out=$(cd "$delrepo" && "$gate" README.md keep.txt); rc=$?
check "a staged deletion mixed with a live file skips the deletion and still flags the live file" \
  1 'keep\.txt:2: ghp_' 'ERROR' "$out" "$rc"

# An UNSTAGED deletion of a tracked file is the other half of todo 944, and the two need
# different git questions: `git rm` above drops the path from the index, so `diff --cached`
# says D while ls-files misses it; here the file is merely gone from disk, so `diff --cached`
# says nothing while ls-files still finds it. This is the shape complete-todo.ps1 produces on
# every archive (Move-Item plus a `git add` of the destination only), which is how a /commit
# run hit it for real on 2026-09-10.
printf 'seed\n' > "$delrepo/archived.md"
git -C "$delrepo" add archived.md
git -C "$delrepo" commit -q -m "add archived.md"
rm -f "$delrepo/archived.md"
out=$(cd "$delrepo" && "$gate" archived.md); rc=$?
check "an unstaged deletion of a tracked file is skipped, not a repo-resolution failure" \
  0 '' 'ERROR' "$out" "$rc"

# --- prefilter-gate.sh: missing but NOT staged for deletion still exits 2 (todo 944) ---
# Mechanical distinction from the three cases above: neither git question recognises this exact
# path - not staged for deletion, not in the index - so it is a typo or wrong cwd, not a deletion.
bogus=$(new_repo); tmp_dirs+=("$bogus")
out=$(cd "$bogus" && "$gate" never/existed.txt); rc=$?
check "a path that was never tracked and is not on disk still exits 2" \
  2 'ERROR: could not find a git repository for never/existed\.txt' '' "$out" "$rc"

# --- comment-noise.sh: generated-file skip, filename suffix only (done/456) ---
# comment-noise.sh's own exit code is sort's (always 0), so this checks stdout content only;
# the gate integration is already covered by the secret-scan cases above.
gen=$(new_repo); tmp_dirs+=("$gen")
write_noisy() {
  local path=$1 i
  : > "$path"
  for i in 1 2 3 4 5 6; do printf '// note %d\n' "$i" >> "$path"; done
  for i in $(seq 1 18); do printf 'var x = %d;\n' "$i" >> "$path"; done
}
write_noisy "$gen/model.freezed.dart"
write_noisy "$gen/model.dart"
mkdir -p "$gen/generated"
write_noisy "$gen/generated/model.dart"
out=$(cd "$gen" && bash "$comment_noise" model.freezed.dart model.dart generated/model.dart)
if printf '%s' "$out" | grep -qF 'model.freezed.dart'; then
  echo "FAIL: comment-noise.sh flagged a .freezed.dart file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qE '^model\.dart '; then
  echo "FAIL: comment-noise.sh did not flag the hand-written model.dart: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qE '^generated/model\.dart '; then
  echo "FAIL: comment-noise.sh skipped a hand-written file merely sitting under generated/: $out"
  fail=1
else
  echo "PASS: comment-noise.sh skips by filename suffix, not by directory"
fi

# --- em-dash.sh: exempt marker honored under .claude/todos/ only (done/778) ---
ed=$(new_repo); tmp_dirs+=("$ed")
mkdir -p "$ed/.claude/todos" "$ed/other"
ED=$(printf '\xe2\x80\x94')
printf '<!-- em-dash-exempt -->\nhas a %s dash\n' "$ED" > "$ed/.claude/todos/exempt.md"
printf 'has a %s dash\n' "$ED" > "$ed/.claude/todos/flagged.md"
printf '<!-- em-dash-exempt -->\nhas a %s dash\n' "$ED" > "$ed/other/outside.md"
out=$(cd "$ed" && bash "$em_dash" .claude/todos/exempt.md .claude/todos/flagged.md other/outside.md)
if printf '%s' "$out" | grep -qF 'exempt.md'; then
  echo "FAIL: em-dash.sh flagged a marked todo file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qF 'flagged.md'; then
  echo "FAIL: em-dash.sh did not flag an unmarked todo file: $out"
  fail=1
elif ! printf '%s' "$out" | grep -qF 'outside.md'; then
  echo "FAIL: em-dash.sh honored the marker outside .claude/todos/: $out"
  fail=1
else
  echo "PASS: em-dash.sh's marker is scoped to .claude/todos/ exactly"
fi

# --- overlap-check.sh: no upstream is clean, a real hunk overlap is a hit ---
noup=$(new_repo); tmp_dirs+=("$noup")
printf 'seed\nline2\n' > "$noup/file.txt"
git -C "$noup" add file.txt
git -C "$noup" commit -q -m "add file"
printf 'seed\nline2 changed\n' > "$noup/file.txt"
out=$(cd "$noup" && "$overlap_check" file.txt); rc=$?
check "overlap-check.sh is clean with no upstream configured" 0 '' '' "$out" "$rc"

remote=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$remote")
git init -q --bare "$remote"
local=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
tmp_dirs+=("$local")
git init -q "$local"
git -C "$local" config user.email "test@example.com"
git -C "$local" config user.name "test"
git -C "$local" config core.autocrlf false
git -C "$local" checkout -q -b master
git -C "$local" remote add origin "$remote"
printf 'line1\nline2\nline3\n' > "$local/f.txt"
git -C "$local" add f.txt
git -C "$local" commit -q -m seed
git -C "$local" push -q -u origin master
printf 'line1\nCHANGED2\nline3\n' > "$local/f.txt"
git -C "$local" commit -q -am "change line2"
printf 'line1\nCHANGED2-AGAIN\nline3\n' > "$local/f.txt"
out=$(cd "$local" && "$overlap_check" f.txt); rc=$?
check "overlap-check.sh reports a hunk-level hit against an unpushed local commit" \
  1 'f\.txt:[0-9]+-[0-9]+ [0-9a-f]{7,40} change line2' '' "$out" "$rc"

# --- foreign-hunk-check.sh: pure deletion reports clean, not foreign (todo 1033) ---
# complete-todo.ps1's archive move (rm + git add of the destination only) leaves the source
# half unstaged - " D" in git status, not a `git rm` - so it has to be reproduced that way,
# not with `git mv`, or git's own rename detection folds the two paths back into one.
fh1=$(new_repo); tmp_dirs+=("$fh1")
mkdir -p "$fh1/.claude/todos/done"
printf 'line one\nline two\nline three\n' > "$fh1/.claude/todos/24-foo.md"
git -C "$fh1" add .claude/todos/24-foo.md
git -C "$fh1" commit -q -m "add todo"
rm "$fh1/.claude/todos/24-foo.md"
printf 'line one\nline two\nline three\n' > "$fh1/.claude/todos/done/24-foo.md"
git -C "$fh1" add .claude/todos/done/24-foo.md
out=$(cd "$fh1" && "$foreign_hunk_check" --own .claude/todos/done/24-foo.md:1-3 \
  .claude/todos/24-foo.md .claude/todos/done/24-foo.md); rc=$?
check "foreign-hunk-check.sh reports a pure deletion clean instead of foreign" \
  0 '24-foo\.md: clean \(pure deletion' '' "$out" "$rc"

# A path with both an added and a removed line is a real modification, not a pure deletion -
# an empty --own must still mark the whole diff foreign, exactly as before this fix.
printf 'a\nb\nc\n' > "$fh1/mixed.txt"
git -C "$fh1" add mixed.txt
git -C "$fh1" commit -q -m "add mixed.txt"
printf 'a\nmine\nforeign\n' > "$fh1/mixed.txt"
out=$(cd "$fh1" && "$foreign_hunk_check" mixed.txt); rc=$?
check "foreign-hunk-check.sh still treats an unattributed real modification as foreign" \
  1 'no own-ranges given, treating entire diff as foreign' '' "$out" "$rc"

# --- foreign-hunk-check.sh: count-less single-line hunk header, no trailing newline (todo 1064) ---
# `@@ -1 +1 @@` omits the ",1" git prints for a multi-line hunk; the no-newline marker line
# that follows must not be miscounted as a content line shifting the own-range off by one.
fh2=$(new_repo); tmp_dirs+=("$fh2")
printf '3.47.5' > "$fh2/flutter.version"
git -C "$fh2" add flutter.version
git -C "$fh2" commit -q -m seed
printf '3.47.6' > "$fh2/flutter.version"
out=$(cd "$fh2" && "$foreign_hunk_check" --own flutter.version:1-1 flutter.version); rc=$?
check "foreign-hunk-check.sh covers a count-less no-newline single-line hunk with own-range 1-1" \
  0 'flutter\.version: clean' '' "$out" "$rc"

# --- em-dash.sh: a text-heavy binary (PDF) is skipped, not scanned (todo 986) ---
# Git's own binary sniff only checks the first ~8KB for a NUL byte; a PDF whose early bytes
# are plain-text structure (as real PDFs are) clears that check and is handed to the scanner
# as if it were prose, so the extension has to gate it independently of git's heuristic.
edbin=$(new_repo); tmp_dirs+=("$edbin")
ED=$(printf '\xe2\x80\x94')
{
  printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nBT /F1 12 Tf (hello%sworld) Tj ET\n' "$ED"
  head -c 9000 /dev/zero | tr '\0' 'x'
} > "$edbin/doc.pdf"
out=$(cd "$edbin" && bash "$em_dash" doc.pdf 2>/dev/null); rc=$?
check "em-dash.sh does not flag a text-heavy PDF containing an em dash" 0 '' 'doc\.pdf' "$out" "$rc"

printf 'hello%sworld\n' "$ED" > "$edbin/note.md"
out=$(cd "$edbin" && bash "$em_dash" note.md 2>/dev/null); rc=$?
check "em-dash.sh still flags an em dash in a plain-text file" 0 'note\.md:1' '' "$out" "$rc"

# --- secret-scan.sh: a text-heavy binary (PDF) is skipped, not scanned (todo 1086) ---
# Same text-like-PDF shape as em-dash.sh's case above: plain-text structure in the first bytes,
# no NUL in the first 8KB, so git's own binary sniff treats it as scannable text. A credential
# embedded in that "text" must not be flagged - the file is binary by extension regardless of
# what git's heuristic says.
ssbin=$(new_repo); tmp_dirs+=("$ssbin")
fake_tok4="ghp_""abcdefghij1234567890abcdef"
{
  printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nBT /F1 12 Tf (api_key = "%s") Tj ET\n' "$fake_tok4"
  head -c 9000 /dev/zero | tr '\0' 'x'
} > "$ssbin/doc.pdf"
out=$(cd "$ssbin" && "$gate" doc.pdf); rc=$?
check "secret-scan.sh does not flag a credential embedded in a text-heavy PDF" 0 '' 'ghp_' "$out" "$rc"

printf 'const tok = "%s";\n' "$fake_tok4" > "$ssbin/config.js"
out=$(cd "$ssbin" && "$gate" config.js); rc=$?
check "secret-scan.sh still flags the same credential in a plain-text file" 1 'config\.js:1: ghp_' '' "$out" "$rc"

# --- comment-noise.sh: a text-heavy binary (PDF) is skipped, not scanned (todo 1086) ---
cnbin=$(new_repo); tmp_dirs+=("$cnbin")
{
  printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
  for i in 1 2 3 4 5 6; do printf '// note %d\n' "$i"; done
  for i in $(seq 1 18); do printf 'var x = %d;\n' "$i"; done
  head -c 9000 /dev/zero | tr '\0' 'x'
} > "$cnbin/doc.pdf"
out=$(cd "$cnbin" && bash "$comment_noise" doc.pdf)
if printf '%s' "$out" | grep -qF 'doc.pdf'; then
  echo "FAIL: comment-noise.sh flagged a text-heavy PDF: $out"
  fail=1
else
  echo "PASS: comment-noise.sh does not flag a text-heavy PDF"
fi

# --- prefilter-gate.sh: CRLF/LF conversion warning never prints, exit code unchanged (todo
# 1115) - new_repo()'s own `core.autocrlf false` exists specifically so no fixture ABOVE this
# one ever hits this warning, so this test builds a dedicated autocrlf=true repo: the exact
# setting that makes each wrapped script's plain `git diff` on a tracked, edited file print
# "LF will be replaced by CRLF" (confirmed empirically - the warning comes from em-dash.sh/
# secret-scan.sh/comment-tense.sh's OWN git diff calls, not from prefilter-gate.sh itself,
# which is why the suppression has to go through the environment rather than a `-c` flag on a
# call this script doesn't make) ---
crlf=$(mktemp -d) || { echo "FAIL: mktemp -d (crlf)"; exit 1; }
tmp_dirs+=("$crlf")
git -C "$crlf" init -q
git -C "$crlf" config user.email "test@example.com"
git -C "$crlf" config user.name "test"
git -C "$crlf" config core.autocrlf true
printf 'line1\nline2\n' > "$crlf/f.txt"
git -C "$crlf" add f.txt
git -C "$crlf" commit -q -m seed
printf 'line1\nline2 EDITED\n' > "$crlf/f.txt"
out=$(cd "$crlf" && "$gate" f.txt 2>&1); rc=$?
check "prefilter-gate.sh suppresses the LF/CRLF conversion warning, exit code unchanged" \
  0 '' 'will be replaced by CRLF|will be replaced by LF' "$out" "$rc"

# --- todo-ref.sh: a numbered todo-id comment is flagged, a bare marker is not (backlog item
# number eleven-twenty-five, spelled out so this comment doesn't trip its own new check) ---
tr1=$(new_repo); tmp_dirs+=("$tr1")
printf 'function x() {\n  // todo 44 fix: something\n}\n' > "$tr1/code.js"
out=$(cd "$tr1" && "$gate" code.js); rc=$?
check "todo-ref.sh flags an added '// todo NN' comment" \
  1 'todo-ref\.sh' '' "$out" "$rc"

printf 'function y() {\n  // TODO: handle null\n}\n' > "$tr1/code2.js"
out=$(cd "$tr1" && "$gate" code2.js); rc=$?
check "todo-ref.sh does not flag a bare TODO marker with no number" \
  0 '' 'todo-ref\.sh' "$out" "$rc"

printf 'See todo 44 for context.\n' > "$tr1/notes.md"
out=$(cd "$tr1" && "$gate" notes.md); rc=$?
check "todo-ref.sh exempts markdown files" \
  0 '' 'todo-ref\.sh' "$out" "$rc"

printf 'def f():\n    # Todo #12 handle edge case\n    pass\n' > "$tr1/code.py"
out=$(cd "$tr1" && "$gate" code.py); rc=$?
check "todo-ref.sh flags a 'Todo #NN' python comment case-insensitively" \
  1 'todo-ref\.sh' '' "$out" "$rc"

mkdir -p "$tr1/.claude/todos"
printf '# todo 44 inside the todos tree\n' > "$tr1/.claude/todos/scratch.py"
out=$(cd "$tr1" && "$gate" .claude/todos/scratch.py); rc=$?
check "todo-ref.sh exempts anything under .claude/todos/" \
  0 '' 'todo-ref\.sh' "$out" "$rc"

printf 'function z() {\n  // see todo 11255 for why\n}\n' > "$tr1/code3.js"
out=$(cd "$tr1" && "$gate" code3.js); rc=$?
check "todo-ref.sh flags a five-digit todo id" \
  1 'todo-ref\.sh' '' "$out" "$rc"

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
