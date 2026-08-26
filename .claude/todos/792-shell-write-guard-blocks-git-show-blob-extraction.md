<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The shell-write guard blocks `git show <sha>:<path> > file`, which extracts a blob rather than authoring content

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/shell-content-write-guard.py` firing on a redirect whose content comes from a git
object, so the standard way of getting a file's committed version onto disk stops being blocked.

## Context

Hit 2026-08-25 in `~/.claude` while verifying todo `401`'s refactor. The command was:

```
git show HEAD:skills/e2e/scripts/design_diff.py > C:/tmp/orig_dd.py
```

The intent was to run the pre-refactor version of a script side by side with the refactored one and
diff their outputs, which is the strongest available proof that a pure refactor changed no
behaviour. The guard rejected it:

> `>` redirect writes file content to `C:/tmp/orig_dd.py` through the shell. Use the Write tool
> instead, or `[System.IO.File]::WriteAllText($path, $text)` when a script genuinely must write.

**Neither suggested alternative works here.** The Write tool needs the content in the agent's
context, which means reading the whole old file in just to write it back out - the exact cost the
redirect avoids, and pointless for a file being handed straight to another process.
`WriteAllText` has the same problem. The guard's own rationale is the PS 5.1 UTF-8 BOM corruption
that `Set-Content`/`Out-File`/`>` cause, and that reasoning does not reach this case: the bytes
originate from a git object, the destination is a scratch file no parser of ours reads as config,
and `git` writes its own stdout without a BOM.

The rule this enforces (global `CLAUDE.md`, Shell Commands) is a **hard ban on the write mechanism**,
deliberately, so this is not obviously a bug - but blob extraction is a distinguishable case, and
blocking it removes a real verification technique rather than a footgun.

**This is at least the fourth false-positive class on this guard.** Todo `476` records a `>` that is
a comparison operator inside a heredoc body, and `790` covers quoted angle brackets. A guard
accumulating false-positive classes is the shape this repo's own hook doctrine says to re-measure
rather than keep patching.

## Approach

1. Reproduce it, then decide between three, and record which:
   - **Carve out the source:** allow a redirect whose command is a pure git read
     (`git show`/`git cat-file`) into a path outside the repo. Narrow, and the BOM rationale
     provably does not apply.
   - **Carve out the destination:** allow any redirect into a scratch dir (`C:/tmp/`, `$env:TEMP`).
     Broader, and weakens the rule for genuine config writes that happen to be staged in temp.
   - **Do nothing, document the workaround.** `git show <sha>:<path> | python -` covers piping to a
     process; a worktree covers needing the file on disk. Cheapest, and keeps the ban absolute.
2. Whichever is chosen, measure against the transcript corpus FIRST, per this repo's hook doctrine
   ("measure against a real corpus BEFORE wiring anything"): count how often a `git show` redirect
   appears in real history versus how often a genuine BOM-hazard write does. Three heuristic hooks
   were deleted here on 2026-08-20 for skipping that step.
3. **Consider whether 476, 790 and this one want one fix, not three.** Four false-positive classes
   on one guard is the signal the doctrine names for re-deriving a detector rather than patching it
   again. That is a bigger call than this todo alone and should be raised, not decided quietly.
4. If a carve-out ships, add its case to `hooks/test_shell_content_write_guard.py` so
   `ci/run_all.py` covers it.

## Acceptance

- The chosen option is implemented or the decision to do nothing is written down with its reasoning.
- If a carve-out shipped: `git show HEAD:<path> > <scratch>` is allowed, a bare
  `echo "..." > config.json` is still blocked, and both are covered by tests.
- The corpus measurement from step 2 is recorded, whatever it showed.
- `python ci/run_all.py` passes.

## Notes

Joe was told about this at close on 2026-08-25 and it was filed rather than fixed on the spot,
because changing a guard mid-session means the session edits the hook currently policing it -
`PLAN.md`'s "three tips that matter" warns against exactly that.
