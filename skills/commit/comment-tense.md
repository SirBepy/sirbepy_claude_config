# Timeless Present check

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2). Read on demand -
not part of either skill's always-loaded body.

## Timeless Present (enforced)

A comment is written for someone meeting the code for the first time, so it states what IS,
never what changed. `// Added mutex to fix race condition` is a changelog entry stranded in the
source: six months on the reader does not know which race, cannot tell whether the mutex is
still needed, and does not care that it was added. `// Mutex serializes cache access from
concurrent requests` states the invariant instead. Checked by `comment-tense.sh` in the same
prefilter, which is deliberately high-precision and low-recall - it flags a change verb opening
a comment block (`Added`/`Removed`/`Renamed`/`Replaced`/`Refactored`/`Migrated`/`Bumped`), plus
`we decided to`, `unlike the old`, `as of this change` and `TODO from the`. Measured 2026-08-22
over the whole tracked tree as one all-added diff: **1 hit in 86 code files**, and that one is
arguably genuine. Bare `no longer` and `previously` were tried and CUT - they produced 36 hits,
nearly all legitimate, because both are ordinary ways to state a current invariant. Known recall
gap: inside an unbroken run of `//` lines only the first is checked, which is the price of not
flagging wrapped continuations.

If step 5a flags a tense hit: rewrite the flagged comment to state what the code IS, never what
changed about it - never just reword it to dodge the regex.

**Invisible-path scanning is a shared helper, not two copies (todo 853).** Both prefilters
(`secret-scan.sh`, `em-dash.sh`) classify a passed path as tracked / untracked-visible /
invisible and scan the invisible ones via `--no-index`, so a gitignored file a caller names on
purpose still gets read (todo 460/804). Todo 804 declined to extract this because no shared lib
file existed yet and an array-returning helper crossing a shell boundary was a real quoting risk.
Todo 813 then built `_prefilter-lib.sh` and proved dot-sourcing works for `git_c`, which removes
the first half of that reasoning; the second half (the quoting risk) does not apply to this
specific block either, because `scan_invisible_paths` is dot-sourced into the caller's own shell
and takes `"$@"` directly, printing its result to stdout for the caller to pipe onward, so there
is no array to marshal back across any boundary. Extracted into `_prefilter-lib.sh` on that
basis.
