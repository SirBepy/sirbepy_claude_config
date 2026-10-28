<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# secret-scan.sh reports clean on a gitignored file without reading a byte of it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/secret-scan.sh` (and its two sibling prefilters) distinguish "I read this file
and it is clean" from "I could not see this file at all", so a gitignored path can never be reported
as audited when it was never scanned.

## Context

Found 2026-08-20 while executing todo 415, which required auditing `settings.local.json` for secrets
before deciding whether to track it. The todo's own Approach step 2 said to run
`skills/commit/secret-scan.sh` against that file. Real invocation from this session:

```
$ bash skills/commit/secret-scan.sh settings.local.json
$ echo $?
0
```

Empty output, exit 0, which `/commit` step 5a's contract reads as "clean". Nothing was scanned.

**Mechanism.** `secret-scan.sh:44-47` builds its diff from two sources: `git diff HEAD -- "$@"` for
tracked files, and `git ls-files --others --exclude-standard -z -- "$@"` for untracked ones.
`~/.claude/.gitignore` is deny-all-then-allowlist (`*` plus `!` exceptions) and never excepts
`settings.local.json`, so the file is IGNORED, and `--exclude-standard` is exactly the flag that
drops ignored files from `ls-files --others`. Neither source yields it, awk gets an empty stream, and
the script's own documented "no output means clean" convention does the rest.

The audit in 415 was completed by reading the file directly instead, which is why that todo did not
ship a false all-clear. The next caller may not notice.

**Same silent-pass family as todo 412** (the prefilters are blind inside a git submodule, because a
parent repo tracks a submodule as one gitlink), but a different mechanism with a different fix: a
submodule-aware re-run does nothing for an ignored path, and vice versa. Filed separately for that
reason, deliberately cross-referenced here. Whoever picks up either one should read the other first;
the right answer may be one shared "did I actually see this file" precondition serving both.

## Approach

1. Reproduce before fixing, in this repo: `bash skills/commit/secret-scan.sh settings.local.json`
   must be seen returning empty with exit 0 while the file demonstrably exists and has content. **Do
   not write a fix before seeing that**, same reasoning as 412: the entire finding is that a no-op
   looks identical to a pass.
2. Add a visibility precondition rather than widening the scan. For each passed path, classify it:
   tracked, untracked-and-visible, or invisible (`git check-ignore -q <path>` succeeds, or the file
   does not exist). Candidates for the invisible case, pick one deliberately:
   - **Refuse loudly.** Print `ERROR: cannot inspect <path> (gitignored)` and exit non-zero, matching
     the script's existing `ERROR:` convention for an uninspectable untracked file (`secret-scan.sh`
     already does exactly this when `git diff --no-index` fails, so the shape is established).
   - **Scan it anyway** via `git diff --no-index -- /dev/null <path>`, the same call the untracked
     branch already uses, just without the `ls-files` gate in front of it.
   Recommended: scan it anyway, because a caller who explicitly named the path wants it audited, and
   refusing turns a deliberate audit into a dead end. Refuse-loudly is the acceptable fallback if
   scanning ignored paths turns out to produce noise for real commits.
3. Whatever lands, apply it to all three prefilters or state why not. `comment-noise.sh` and
   `em-dash.sh` share the same `git diff HEAD` + `ls-files --others --exclude-standard` shape, so they
   have the same blind spot; they are lower stakes than `secret-scan.sh` but the inconsistency is its
   own trap.
4. `prefilter-gate.sh` needs no change if the scripts keep their exit-code contract, but confirm its
   labeled output still attributes an ERROR line to the right script.

## Acceptance

- A secret planted in a gitignored file makes the chosen behaviour fire: exit non-zero either way,
  with output that names the file. Prove it by planting one, running the script, and removing it - a
  green run on an unmodified ignored file proves nothing, which is the bug.
- `bash skills/commit/secret-scan.sh settings.local.json` no longer exits 0 silently.
- A normal commit's behaviour is unchanged: run the gate against a real tracked-file diff and show
  the output is identical to today's.
- `python ci/run_all.py` still exits 0.

## Notes

Do not fix this by removing `--exclude-standard`. That would pull every ignored file in the passed
path's scope into the scan (in this repo, a deny-all `.gitignore` means nearly everything), which is
a different bug in the other direction. The distinction that matters is per-path and explicit: the
caller named this file, so audit this file.
- Done 2026-08-26: secret-scan.sh classifies each named path as tracked, untracked-visible, or invisible-to-git, and scans the invisible ones through the same git diff --no-index call the untracked branch already used. Verified end to end: the pre-460 script was silent (exit 0, no output) on a gitignored file holding a planted AWS key, and prefilter-gate.sh now exits 1 naming it, while a clean gitignored file still exits 0 and a normal tracked-plus-untracked call is byte-identical old versus new. Correction to this todo's own Acceptance text: it asked for exit non-zero on a hit, but the script has NEVER exited non-zero on a hit - its exit status is sort's, from the tail of the pipe, and prefilter-gate.sh flags on non-empty output rather than exit code. That was verified against the unmodified script rather than assumed, and deliberately left unchanged as out of scope. Still open: comment-noise.sh has the identical blind spot and needs the same treatment. Filed the same day as todo 804, so it is tracked, not lost. (This sentence originally read "reported and not filed", describing the state at the moment the builder reported it and before 804 was written; a later reviewer read it as a live process gap, so it is corrected here rather than left to mislead again.)
