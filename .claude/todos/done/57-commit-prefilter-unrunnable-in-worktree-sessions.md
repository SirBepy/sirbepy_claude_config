<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# comment-noise prefilter command is unrunnable in worktree-isolated sessions

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` step 5a's comment-noise prefilter runnable as written when the session is isolated in
a git worktree. Today it is refused outright and has to be hand-split every time.

## Context

Observed 2026-08-08 in `claude_usage_in_taskbar`, session working in
`.claude/worktrees/android-shell`.

`commit/SKILL.md` step 5a specifies a single command shaped like:

```
{ git diff HEAD -- <files>; git status --porcelain -- <files> | awk ... | while read f; do git diff --no-index -- /dev/null "$f"; done; } | awk '...'
```

In a worktree-isolated session the harness refuses it with:

> "this command is too complex to verify that it stays inside the worktree; break it into plain,
> separate commands. Refusing to run it - a worktree-isolated session's git operations must target
> its own worktree."

The compound `{ ...; ... }` block plus the embedded `while` loop is what trips the guard, not
anything about the paths. So the check cannot run in the form the skill mandates.

The workaround, used twice this session: dump the diff to a file with a plain single command
(`git diff HEAD -- <files> > /tmp/cn.diff`), then run the `awk` program against that file as a
second plain command. Two calls instead of one, identical output.

**Why this matters rather than being cosmetic:** step 8 makes the prefilter a hard precondition on
committing ("has step 5a's prefilter actually been run against this exact pathspec, this turn").
A check that is mandatory AND refused by the harness invites exactly the thing step 8 warns against,
committing first and rationalising the check afterward. It should not depend on a session noticing
the refusal and improvising.

Also note the untracked-file pass is what forces the compound shape, and it is frequently redundant:
if the new files are already staged, `git diff HEAD` sees them and the second half contributes
nothing.

## Approach

1. In `commit/SKILL.md` step 5a, replace the single compound command with the two-step form as the
   DEFAULT, not as a fallback: dump diff to a temp file, then `awk` the file. It works identically
   in both worktree and non-worktree sessions, so there is no reason to keep two variants.
2. State explicitly that when every file in the pathspec is already tracked or staged, the
   untracked-file pass can be dropped entirely, which removes the `while` loop.
3. Apply the same change to `/create-pr`'s range-mode variant of the command, and to
   `skills/commit/comment-noise.md`, which SKILL.md names as the single place the command is
   defined. All three must stay in sync or this recurs.

## Acceptance

- The documented command runs unmodified in a worktree-isolated session.
- `comment-noise.md`, `commit/SKILL.md` and `/create-pr` all carry the same form.

## Notes

- Distinct from todo 56, which is about the prefilter's ACCURACY (false positives on moved code).
  This one is about it being unrunnable as written. Fixing either does not fix the other, though
  both touch the same command and could be done in one pass.

- Re-verified 2026-08-08: premise still holds.
- Duplicate of 45 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.