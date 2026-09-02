<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The mega-todos builder commit block omits /commit's working-tree diff check, so a builder swept a human's edit

**Type:** skill-improvement
**Origin:** ai

## Goal

Add `/commit` step 8's working-tree diff check to the injected commit block in
`skills/mega-todos/SKILL.md`, so a builder committing a shared file cannot silently carry a
concurrent session's uncommitted hunk into its own commit.

## Context

Happened 2026-09-01, in the `/mega-todos` run of that date, batch 2, commit `8419219`.

Todo 458's builder added a hook entry to `settings.json` and committed by pathspec. At that moment
a concurrent human session had its own uncommitted edit in the same file, changing the top-level
`"model"` key from `opus` to `sonnet`. A pathspec commit takes the file's ENTIRE working-tree
state, so that unrelated one-line change landed inside a commit titled
"FEAT: guard reminds a session to check peers before its first edit".

Nothing was lost and the value on disk is the one the human intended, so this was NOT reverted:
the branch is shared and rewriting it is the one action guaranteed to hurt someone else's work.
The damage is a misattributed hunk in history, which is cheap now and confusing later.

The orchestrator's brief for that dispatch did say, verbatim, "never touch the top-level `model`
key - a human session changed it and that change is deliberate". The builder complied: it never
edited that key. The instruction was simply the wrong shape for the hazard. A builder cannot
exclude a hunk from a file it is committing whole, so telling it not to EDIT something says
nothing about what it COMMITS.

`/commit` step 8 already carries the right control and states the reason exactly:

> run `git diff -- <every pathspec entry>` immediately before `git commit`. Account for every hunk
> shown. An unrecognised hunk - one you did not write this session - is a STOP.

The injected block in `skills/mega-todos/SKILL.md` reproduces `/commit`'s marker step, prefilter
step, branch guard and pathspec form, but not this one. Its step 2 says only "Run `git status` and
`git diff` scoped to YOUR files only", which reads as orientation, not as a gate with a STOP.

This is strictly worse under `/mega-todos` than under a normal `/commit`, because the whole point
of that skill is many agents committing into one tree at once.

## Approach

1. Read `/commit` step 8's working-tree diff check and the injected block in
   `skills/mega-todos/SKILL.md`, and confirm the omission rather than trusting this write-up.
2. Promote the block's step 2 into a real gate: name the command, say every hunk must be accounted
   for, and state the STOP explicitly, including the two permitted resolutions `/commit` already
   defines (drop the path from the pathspec, or announce on the repo channel that you are taking
   the file whole and name whose lines ride along).
3. Decide whether a builder that hits an unrecognised hunk should stop and report, or drop that
   path and commit the rest. Dropping the path is probably right for a wide parallel run, since one
   shared config file should not stall an otherwise-clean lane. Say which you chose and why.
4. Check whether the same omission exists in the `barrier` COMMIT_MODE half of that file, where the
   main thread commits instead of the builder.
5. Consider whether a shared config file like `settings.json` should be excluded from builder
   ownership altogether under this skill, with the orchestrator applying such edits at a barrier.
   That would remove the hazard rather than documenting it, at the cost of serialising those edits.

## Acceptance

- The injected commit block names the `git diff -- <paths>` check, the account-for-every-hunk rule,
  and an explicit STOP with its permitted resolutions.
- The `barrier` COMMIT_MODE section carries the same control, or explicitly says why it does not
  need it.
- The chosen answer to step 3 is written down in the block itself, not left to the builder.
- `python ci/run_all.py` exits 0, and every path the changed markdown references resolves on disk.

## Notes

Worth pairing with todo 806 (shared-worktree foreign-hunk check helper) if that lands first: a
scripted check is a stronger control here than a paragraph a builder has to remember, and this todo
is the concrete incident that justifies building it.
