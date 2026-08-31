<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=225d795e -->
<!-- duplicate-checked -->
# comment-noise.sh and em-dash.sh still report clean on a file git cannot see

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `comment-noise.sh` and `em-dash.sh` the same invisible-path handling todo 460 just gave
`secret-scan.sh`, so none of the prefilters can report clean on a file it never opened.

## Context

Filed 2026-08-26 from todo 460's fix (commit `003338c`), which deliberately scoped itself to
`secret-scan.sh` because the other two scripts were owned by concurrent dispatches at the time.

All three scripts find content the same way: tracked changes via `git diff HEAD -- <paths>`, and
new files via `git ls-files --others --exclude-standard -- <paths>`. A gitignored path is in
neither set, so the awk stream is empty and the script prints nothing. Every caller reads "no
output" as clean.

Measured on the pre-460 `secret-scan.sh`, and the mechanism is identical in the other two:

    $ git check-ignore -v settings.local.json
    .gitignore:2:*  settings.local.json
    $ bash skills/commit/secret-scan.sh settings.local.json ; echo exit=$?
    exit=0            # nothing printed, nothing read

460 fixed that one by classifying each named path as tracked / untracked-visible / invisible, and
routing the invisible ones through the same `git diff --no-index -- /dev/null <f>` call the
untracked branch already used. See `skills/commit/secret-scan.sh:88-118` for the shape to copy.

**Lower stakes than 460, deliberately filed separately rather than folded in.** `secret-scan.sh` is
the one prefilter whose whole job is to stop a commit, so a silent pass there is a security hole. A
missed comment-cap breach or em dash in a gitignored file is a style miss, and a gitignored file is
usually not in a commit pathspec at all. The reason to do it anyway is consistency: three scripts
with the same contract should not have two different answers to "what does empty output mean."

## Approach

1. Reproduce on each script before changing it, same shape as the command above. Confirm empty
   output and exit 0. **Do not write a fix before seeing it**, since the whole finding is that it
   looks like a pass.
2. Port 460's classification block into both scripts. Read `skills/commit/secret-scan.sh:88-118`
   first and copy the structure rather than re-deriving it; three near-identical copies of this
   logic is the real cost of this change, so check whether the three can share one helper before
   pasting a third copy. There is no shared helper file under `skills/commit/` today.
3. Decide whether `em-dash.sh` needs it at all. Lean yes for consistency, but if the shared-helper
   route turns out to be fragile, doing only `comment-noise.sh` and recording why is an acceptable
   outcome - say so explicitly rather than leaving it half-done silently.
4. `comment-noise.sh` has a `.md`/`.mdx` carve-out at `:17` and `em-dash.sh` has its own filters.
   Make sure an invisible path still goes through those, not around them.

## Acceptance

- A gitignored file with an over-long comment block makes `comment-noise.sh` print it. Plant one,
  run it, remove it: a green run on a clean file proves nothing, which is the bug being fixed.
- The same for an added em dash and `em-dash.sh`, if item 3 lands.
- A gitignored file with nothing wrong still prints nothing, and that silence now means scanned.
- Every existing shape is byte-identical: clean single path, clean multi-path, a tracked file with a
  real hit, an untracked-but-visible file with a real hit, and `--range <base>`. Capture the before
  behaviour via `git show HEAD:skills/commit/<script>` into a copy placed BESIDE the real script so
  any relative path still resolves, then diff old against new output.
- `python ci/run_all.py` passes. Note in the report that CI does not cover these scripts, so a green
  run is not evidence either way.

## Notes

- Related and closed: `done/460-prefilters-report-clean-on-a-gitignored-file.md`.
- Worth knowing before touching exit codes: none of these scripts exits non-zero on a hit. The exit
  status is `sort`'s, from the tail of the pipe, so it is 0 even when the script prints findings.
  `prefilter-gate.sh` flags on non-empty output OR non-zero exit, which is why the contract still
  works. Verified against the unmodified `secret-scan.sh` on 2026-08-26. Do not "fix" that as a
  drive-by; it is load-bearing for every caller.
- Done via /mega-todos batch 2, commit b040fd3: secret-scan.sh's invisible-path classification loop is ported into both comment-noise.sh and em-dash.sh, feeding the same awk pipeline so invisible paths pass THROUGH each script's carve-outs rather than around them. Builder reproduced the blind spot first on both scripts and verified byte-identical output against the pre-fix baseline for five command shapes. No shared helper introduced, matching the repo's existing 3x duplication of the same loop.
