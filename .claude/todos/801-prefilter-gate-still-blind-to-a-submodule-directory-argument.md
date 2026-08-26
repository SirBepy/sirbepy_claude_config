<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# prefilter-gate.sh is still blind when handed a submodule DIRECTORY instead of a file

**Type:** skill-improvement
**Origin:** ai

## Goal

Close the one path shape todo 412's fix does not cover: a directory argument that IS a submodule
root, or that contains one, still resolves to the parent repo and reads nothing.

## Context

Found 2026-08-26 while verifying todo 412 in `~/.claude` (commit `e61d305`).

412 made `prefilter-gate.sh` group each path argument by its own resolved repo root, via
`git -C "$(dirname -- "$a")" rev-parse --show-toplevel`. That resolves correctly for a FILE inside a
submodule, which was the reported case and is now proven fixed (a planted credential in
`vendor/sub/config.sh` exits 1 where it used to exit 0 silently).

The residual hole is the `dirname` step. For an argument of `vendor/sub` (the submodule root
itself), `dirname` is `vendor`, which lives in the PARENT repo, so `arg_repo` resolves to the
parent and the whole submodule tree goes back to reading as one gitlink entry. Same for `vendor/`
or any ancestor directory of a submodule. The result is the original 412 shape: exit 0, no output,
indistinguishable from clean.

**Why this is worth filing rather than shrugging at:** `/commit`'s step 7 explicitly instructs the
caller to `include <submodule-path> in step 8's commit pathspec` when a submodule pointer is dirty.
That is a DIRECTORY argument, written into the skill as the normal thing to do. So the documented
happy path for a submodule commit produces exactly the invocation shape that no-ops.

Not verified: whether any caller today actually passes that directory to the prefilter gate as
opposed to only to `git commit`. Step 8's chained form is
`prefilter-gate.sh <files> && git commit -m ... -- <files>`, which shares one pathspec between the
two, so it very likely does. Check that before deciding scope.

## Approach

1. Reproduce first, on a scratch parent plus real submodule (412's own fixture recipe works: `git
   init` the sub, `git init` the parent, `git -c protocol.file.allow=always submodule add <path>
   vendor/sub`). Plant a secret inside `vendor/sub`, then run
   `bash skills/commit/prefilter-gate.sh vendor/sub` from the parent root. Confirm exit 0 with no
   output. **Do not write a fix before seeing the empty output.**
2. Resolve a DIRECTORY argument from the directory itself, not from its parent: if `$a` is a
   directory, use `git -C "$a" rev-parse --show-toplevel`; only fall back to `dirname` for a file.
   That alone fixes the submodule-root case, since `git -C vendor/sub rev-parse --show-toplevel`
   returns the submodule's own root.
3. The harder sub-case: a directory that CONTAINS a submodule but is not one (`vendor/`, or the
   repo root itself). Resolving it gives the parent, and any submodule beneath it stays invisible.
   Decide deliberately between expanding it via `git submodule status` and refusing it with a plain
   line. Recommended: refuse, and say which submodules were skipped. A gate that names what it
   could not read is honest; one that silently covers a subtree it did not read is the bug being
   fixed. Record the decision either way.
4. Check whether `/commit` step 7's instruction to put `<submodule-path>` in the pathspec needs a
   note saying the prefilter gate wants the changed FILES inside the submodule, not the gitlink
   directory. Fixing the script without fixing that text leaves the trap in place.

## Acceptance

- A planted secret inside a submodule makes `prefilter-gate.sh <submodule-dir>` exit non-zero.
  Prove it by planting one, running it, and removing it: a green run on an unmodified submodule
  proves nothing, which is the exact failure being fixed.
- A directory argument containing a submodule either reads it or refuses loudly, never exits 0
  silently.
- All seven non-submodule shapes stay byte-identical: clean single path, clean multi-path, zero
  args, `--range <base>`, explicit `-C`, a bad path (exit 2), a bad `--repo` (exit 2). Capture the
  before behaviour via `git show HEAD:skills/commit/prefilter-gate.sh` into a copy placed beside
  the real wrapped scripts, so `$dir` still resolves, and diff the two outputs.
- A plain directory argument in a repo with no submodules behaves as it does today.
- `python ci/run_all.py` passes.

## Notes

- 412's fix is in `skills/commit/prefilter-gate.sh:22-73`. The `dirname` call is the line to change.
- `git rev-parse --show-toplevel` on a path that is a FILE fails, which is why 412 used `dirname` in
  the first place. Any fix has to branch on `-d` rather than replace the call outright.
- Related and already closed: `done/412-commit-prefilters-are-blind-to-submodule-changes.md` (file
  arguments, fixed), `done/447-prefilter-gate-has-no-repo-target-so-cross-repo-commits-break.md`
  (repo discovery, fixed).
