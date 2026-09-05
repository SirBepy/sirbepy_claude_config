# Comment-noise and Timeless Present checks

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2). Read on demand -
not part of either skill's always-loaded body. Two independent checks live here.

## Comment-noise (informational only, todo 922)

Demoted 2026-09-05: this length/ratio scan no longer gates a commit. `prefilter-gate.sh` still
runs `comment-noise.sh` and prints whatever it flags, but never lets that output set the gate's
exit status, so a long comment block never blocks a commit. The measurement stays wired up for
the parked todo 403 brainstorm on what the rule should be. For the actual guidance a comment
should follow now, see `CLAUDE.md`'s Code Style section: say why, not what; an opaque-code line
(a dense regex, bit-twiddling, a non-obvious algorithm) can earn a one-line what.

Mechanical scan, unchanged plumbing - a real script rather than inline in this file, since
skill-argument substitution rewrites a bare `$0` found in a skill's own body text, which used to
clobber awk's `$0` ("whole current line") every time this was pasted inline:

```
bash skills/commit/comment-noise.sh <file> <file> ...   # working-tree mode, /commit step 5a
bash skills/commit/comment-noise.sh --range <base>       # range mode, /create-pr branch diff
```

No output means nothing was flagged. `.md`/`.mdx` files are skipped entirely - a `#` there is a
heading, never a comment (todo 340). Generated output is skipped by filename suffix
(`.freezed.dart`, `.g.dart`, `.pb.go`, `.pb(enum|json|server).dart`, `_pb2.py(i)`,
`.generated.*`), never by directory, so a hand-written file under a `generated/` folder is still
scanned (todo 456). Rust trap: the `#` regex counts `#[attribute]` lines as comments too, so a
4-line `///` doc block sitting right above one attribute still gets flagged.

## Timeless Present (still enforced)

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

**Invisible-path scanning is a shared helper, not three copies (todo 853).** All three
prefilters (`comment-noise.sh`, `secret-scan.sh`, `em-dash.sh`) classify a passed path as
tracked / untracked-visible / invisible and scan the invisible ones via `--no-index`, so a
gitignored file a caller names on purpose still gets read (todo 460/804). Todo 804 declined to
extract this because no shared lib file existed yet and an array-returning helper crossing a
shell boundary was a real quoting risk. Todo 813 then built `_prefilter-lib.sh` and proved
dot-sourcing works for `git_c`, which removes the first half of that reasoning; the second half
(the quoting risk) does not apply to this specific block either, because `scan_invisible_paths`
is dot-sourced into the caller's own shell and takes `"$@"` directly, printing its result to
stdout for the caller to pipe onward, so there is no array to marshal back across any boundary.
Extracted into `_prefilter-lib.sh` on that basis.

A block flagged by comment-noise only because it moved verbatim into a new file (a pure code
move, wording unchanged) is not new noise - confirm via `git show HEAD:<old-file>` before
dismissing it. The exemption covers unchanged text moved as-is only; a newly authored comment
sitting in a moved file is still a hit.
