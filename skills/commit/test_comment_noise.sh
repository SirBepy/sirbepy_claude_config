#!/usr/bin/env bash
# Self-test for comment-noise.sh's cut arithmetic (todo 903). No harness runs this yet; invoke
# directly: bash skills/commit/test_comment_noise.sh
set -uo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
# comment-noise.sh itself always exits 0 (it only ever prints); prefilter-gate.sh is what turns
# its nonempty stdout into exit 1, so "clears the gate" is asserted through the gate, not the leaf.
gate="$script_dir/prefilter-gate.sh"

fail=0
tmp=$(mktemp -d) || { echo "FAIL: mktemp -d"; exit 1; }
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

git -C "$tmp" init -q
git -C "$tmp" config user.email "test@example.com"
git -C "$tmp" config user.name "test"
printf 'seed\n' > "$tmp/README.md"
git -C "$tmp" add README.md
git -C "$tmp" commit -q -m seed

# n_code/n_comment code lines then 1 comment, repeated n_comment times, leftover code appended
# at the end - exact totals with no comment run >= 2, isolating the ratio arithmetic under test.
write_case() {
  local path=$1 n_comment=$2 n_code=$3
  : > "$path"
  local per=$((n_code / n_comment))
  local placed_code=0 c=0
  while [ "$c" -lt "$n_comment" ]; do
    local j=0
    while [ "$j" -lt "$per" ]; do printf 'var x = 1;\n' >> "$path"; placed_code=$((placed_code + 1)); j=$((j + 1)); done
    printf '// note\n' >> "$path"
    c=$((c + 1))
  done
  while [ "$placed_code" -lt "$n_code" ]; do printf 'var x = 1;\n' >> "$path"; placed_code=$((placed_code + 1)); done
}

check() {
  local desc=$1 expected_exit=$2 expect_pattern=$3 actual_out=$4 actual_exit=$5
  if [ "$actual_exit" != "$expected_exit" ]; then
    echo "FAIL: $desc - exit $actual_exit, want $expected_exit"
    fail=1
    return
  fi
  if [ -n "$expect_pattern" ] && ! printf '%s' "$actual_out" | grep -qE "$expect_pattern"; then
    echo "FAIL: $desc - output did not match /$expect_pattern/: $actual_out"
    fail=1
    return
  fi
  echo "PASS: $desc"
}

# Case 1: exact 25% boundary (12/48) must report a nonzero cut, never "cut 0" (the reported bug).
write_case "$tmp/exact.js" 12 36
out=$(cd "$tmp" && "$gate" exact.js); rc=$?
check "exact 25% boundary reports cut 1, not cut 0" 1 '12/48 \(25%\).*-> cut 1 comment lines' "$out" "$rc"

# Case 2: acting on the printed cut for the reported 13/49 (26%) case clears the gate in one retry.
write_case "$tmp/reported.js" 13 36
out=$(cd "$tmp" && "$gate" reported.js); rc=$?
check "13/49 (26%) reports cut 2" 1 '13/49 \(26%\).*-> cut 2 comment lines' "$out" "$rc"

sed -i '0,/^\/\/ note$/{/^\/\/ note$/d}' "$tmp/reported.js"
sed -i '0,/^\/\/ note$/{/^\/\/ note$/d}' "$tmp/reported.js"
out=$(cd "$tmp" && "$gate" reported.js); rc=$?
check "cutting 2 lines from 13/49 clears the gate in one retry" 0 '' "$out" "$rc"

# Case 3: well under the cap - no flag, exit 0.
write_case "$tmp/clean.js" 5 40
out=$(cd "$tmp" && "$gate" clean.js); rc=$?
check "5/45 (11%) is clean" 0 '' "$out" "$rc"

if [ "$fail" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi
exit "$fail"
