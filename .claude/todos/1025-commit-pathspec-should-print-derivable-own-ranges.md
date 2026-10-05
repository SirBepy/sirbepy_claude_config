<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 924 and 933 cover WHY the own-range derivation refuses under multiple session markers (correctness). This is about what it PRINTS when it refuses (ergonomics). Do not fold: closing this by relaxing the refusal would reopen exactly what 924 fixed. -->
# commit-pathspec.sh should print the ranges it just derived when it refuses

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the caller hand-deriving `--own-range` values that the script already computed a moment
earlier.

## Context

`skills/commit/commit-pathspec.sh` auto-derives each file's own-range from `git diff HEAD`, but
only trusts that derivation when `hooks/.session-markers/` shows one live marker or zero. With two
or more it refuses with `UNVERIFIED`, naming the files and telling the caller to declare
`--own-range` or pass `--force foreign-hunk`. That refusal is correct and deliberate (todo 924's
REOPENED fix, 933 folded in); this todo does not touch it.

The ergonomic problem is what happens next. The script has ALREADY computed the ranges. It just
does not show them. So the caller re-derives the same numbers by hand:

```
git diff --cached -U0 | awk '/^\+\+\+ b\//{f=substr($0,7)} /^@@/{split($3,a,","); s=substr(a[1],2); n=(a[2]==""?1:a[2]); if(n>0) printf "%s:%s-%s\n", f, s, s+n-1}'
```

Measured 2026-09-26 in `server_supervisor`: six commits in one session, three live session markers
throughout (other Conductor sessions in other repos, none sharing this checkout), so every single
commit hit the refusal and every one needed that awk line re-run and its output hand-folded into a
`--own-range` argument per file. One commit spanned 11 files.

The information asymmetry is the whole finding: the script knows the answer and makes the caller
recompute it.

## Approach

- In the `UNVERIFIED` refusal branch, print the derived ranges in exactly the form
  `--own-range "<path>:<lo>-<hi>"`, one per refused file, ready to paste.
- Label them unmistakably as UNVERIFIED and as a starting point the caller must check against their
  own edits, never as a blessed value. The refusal exists because the derivation cannot be trusted
  under concurrency; printing it must not read as "here is the answer, paste it".
- Do NOT relax the refusal, do not add a flag that accepts the derived ranges automatically, and do
  not collapse multiple hunks into one span silently. Any of those reopens todo 924.
- Check first whether the derivation is even reachable at the point of refusal, or whether it is
  computed lazily afterwards. If it is not available there, this may be a bigger change than it
  looks and is probably not worth it; say so and close rather than restructuring the script.

## Acceptance

- Running `commit-pathspec.sh` in a repo with 2+ live session markers prints paste-ready
  `--own-range` arguments alongside the existing refusal text.
- The refusal still refuses. A run that would have been blocked before is still blocked.
- `python ci/run_all.py` passes.

## Notes

Filed 2026-09-26 from a `server_supervisor` session, per root `CLAUDE.md`'s rule that findings about
the global `~/.claude` tree belong in this repo's backlog rather than the surfacing project's.

Worth weighing against just doing nothing: the workaround is a one-line awk invocation and the
refusal is rare for anyone working solo. If the fix is not near-trivial, closing this as won't-do is
a reasonable outcome.
