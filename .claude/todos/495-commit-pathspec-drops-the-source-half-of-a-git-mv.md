<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=46592725 -->
<!-- duplicate-checked -->
# `/commit`'s pathspec form silently drops the source half of a `git mv`, and step 8's diff check cannot see it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` step 8 catch a half-committed file move, instead of producing a commit where the
new copies exist and the old ones are still tracked.

## Context

Hit 2026-08-22 in the `hubbub` repo, during an `/auto-do-todos` run that moved
`packages/ui/src/avatars/` -> `packages/sdk/src/avatars/` and `packages/ui/licenses/` ->
`packages/sdk/licenses/` via `git mv`.

`git mv` stages BOTH halves: an add at the destination and a delete at the source. The commit
pathspec named `packages/sdk/licenses` (destination) but not `packages/ui/licenses` (source), so
`git commit -- <pathspec>` committed the additions and left the three deletions staged. Result:
a commit that carried both copies of every license file. Caught only because `git status --short`
was read immediately afterwards and still showed `D packages/ui/licenses/...`.

**Step 8's existing guards do not cover this, and that is the actual gap:**

- The **working-tree diff check** runs `git diff -- <every pathspec entry>`. Unstaged only, and
  scoped to the pathspec - so a staged deletion at a path NOT in the pathspec is invisible to it
  twice over.
- The **unpushed-overlap check** is about other commits, not about this commit's completeness.
- Nothing in step 8 compares the pathspec against what is currently staged.

`git mv` is common in exactly the commits where this matters most (package moves, refactors), and
the failure is quiet: the commit succeeds, tests still pass (both copies are valid files), and only
a `git status` afterwards reveals it.

Distinct from [[412-commit-prefilters-are-blind-to-submodule-changes]], which is about the three
prefilter scripts returning empty inside a submodule. This one is about step 8 never comparing the
pathspec against the index at all, for ordinary tracked files.

## Approach

Add one check to step 8, next to the working-tree diff check, and keep it cheap enough that it runs
on every commit:

1. Before `git commit`, run `git diff --cached --name-status`.
2. Any staged path NOT covered by this commit's pathspec is a STOP: name it, and either widen the
   pathspec or state deliberately why it is being left behind.
3. Call out the rename case by name in the skill text, since it is the one that produces the
   invisible failure: **a `git mv` is two paths, and the pathspec must name both.**

Watch one interaction before implementing: in a SHARED-index repo another session's staged files
are legitimately present and must not turn every commit into a prompt. The check probably has to
warn-and-name rather than hard-stop when the unnamed staged path is unrelated to this commit's
directories, or be gated on the same shared-checkout detection step 8 already does.

Consider whether this folds into the script proposed in
[[474-commit-step-8s-overlap-check-should-be-a-script]] rather than adding a fourth hand-run check
to an already long step.

Do NOT solve it by relaxing the pathspec rule to `git add -A` - the pathspec form exists to protect
a shared index and that reasoning is unchanged.

## Acceptance

- A rehearsal that `git mv`s a file and then commits with only the destination in the pathspec is
  stopped before the commit lands.
- A normal commit with no staged-but-unnamed paths is not slowed down or made to prompt.
- A shared-index repo with another session's unrelated staged files does not prompt on every commit.
- The skill text names the `git mv` case explicitly, with the two-paths rule stated.

## Notes

- The recovery used on 2026-08-22 was `git commit --amend --no-edit -- <both paths>`, which worked
  because nothing had landed on top yet. Worth naming as the recovery in the skill, since the
  obvious alternative (a follow-up "delete the old copies" commit) leaves a broken intermediate
  commit where the tree carries both copies.

- **Reproduced again 2026-08-25, seven times in one run, via `complete-todo.ps1` rather than a
  literal `git mv`.** That script MOVES a todo from `.claude/todos/<id>-*.md` into `done/`. Each
  archive commit named only the `done/` path in its pathspec, so git kept tracking all seven source
  paths as live files that no longer exist on disk. `git status` showed them as ` D` and nothing in
  `/commit` step 8 flagged it: the working-tree diff check inspects the paths IN the pathspec, and
  the dropped path is by definition not in it. Cleaned up in `eac71d7`.

  Two things this adds to the todo above. First, the trigger is not just `git mv` - **any script
  that relocates a file** produces it, and `complete-todo.ps1` is one every backlog run calls
  repeatedly, which is what turned one mistake into seven. Second, the detection is trivial and
  belongs in step 8: after committing, `git status --porcelain <dir>` showing ` D` for a path the
  commit was supposed to move IS the symptom. Worth pairing the fix with a note in
  `close/ai-todos-format.md` that archiving a todo is a two-path commit.
