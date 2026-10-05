<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-09-27, grepped this backlog and done/ for "foreign-hunk". 985, 989, 994, 1004 and 1025 all concern commit-pathspec.sh's session-marker UNVERIFIED refusal and its ergonomics; done/806 shipped the comparison script and done/924 added the own-range derivation. None covers a path whose diff has no + side at all, which no caller can ever satisfy. -->
# `foreign-hunk-check.sh` cannot pass a pure deletion, so every todo archival exits 1

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/foreign-hunk-check.sh` returns clean for a path that was only deleted, so archiving a
todo stops producing an exit 1 the caller has to recognise and step over by hand every single time.

## Context

Hit twice in one session on 2026-09-27 in `cueline`, once per todo archived (`31` and `24`). It will
fire on every future archival, because archiving is a `git mv` into `done/` and the source half of
that move is a pure deletion.

The mechanics, and why the caller cannot fix it from the outside:

- `complete-todo.ps1` moves `.claude/todos/<id>-<slug>.md` to `.claude/todos/done/<id>-<slug>.md`.
  `git status` shows ` D` for the source and `??` for the destination, and `/commit` step 8 correctly
  requires BOTH paths in the pathspec (that is `done/495`'s whole lesson).
- `foreign-hunk-check.sh` is then called with both paths plus `--own` ranges. The destination is a
  new file, so its range is declarable and it reports `clean`. The **source reports**
  `no own-ranges given, treating entire diff as foreign` **and the script exits 1.**
- A `--own` value is a NEW-file line range, matching `git diff`'s `+` side. A pure deletion has no
  `+` side, so there is no range that can be declared. `git diff HEAD -- <path>` on it yields only
  `-` lines and `delete mode 100644`. The caller is being asked for something that does not exist.

Real output from that session, with every other path clean:

```
docs/decisions.md: clean
src/components/editor/sidebar/tabs/AudioTab.tsx: clean
...
.claude/todos/24-decide-whether-clypra-studio-is-a-brand-to-keep-or-rename.md: no own-ranges given, treating entire diff as foreign
.claude/todos/done/24-decide-whether-clypra-studio-is-a-brand-to-keep-or-rename.md: clean
foreign-hunk exit: 1
```

**Why this matters more than one confusing line.** `/commit` step 8 lists this check as a
precondition and treats exit 1 as a real finding demanding a decision. An exit 1 that is guaranteed,
unavoidable, and meaningless on a routine operation is the textbook way a check becomes reflexive
noise, which is the exact failure 985 already documents for the sibling refusal. Anyone following
the SKILL.md prose literally either stops on a non-problem or learns to skim past a check that
sometimes reports real ones.

`commit-pathspec.sh` already knows about this shape: SKILL.md step 8 says it "excludes an
already-`git rm`'d path from the two checks that cannot diff it while keeping it in the commit". That
exclusion covers a path staged via `git rm`, not a working-tree deletion produced by a script's
`Move-Item`, which is what `complete-todo.ps1` actually does, so the archival case falls straight
through it.

## Approach

1. In `skills/commit/foreign-hunk-check.sh`, before the own-range comparison, detect a pure deletion
   for each path: `git diff HEAD --summary -- <path>` contains `delete mode`, or equivalently the
   diff has zero added lines. Report it as `clean (pure deletion, no added lines to attribute)` and
   do not let it set exit 1.
   - Keep it narrow. A file with BOTH deletions and additions is a normal modification and must stay
     subject to the check. Only a diff with a zero-length `+` side qualifies.
2. Do the same in `commit-pathspec.sh` so its bundled call agrees, and widen its existing
   `git rm`-only exclusion to cover a working-tree deletion.
3. Add a self-test alongside the other `hooks/test_*.py` suites, or in `ci/`, that stages a deleted
   path plus a modified path and asserts the script exits 0 with the deletion reported clean and the
   modification still checked.
4. While in `skills/commit/SKILL.md` step 8, correct the sentence about excluding an "already
   `git rm`'d path" so it names working-tree deletions too, since `complete-todo.ps1` is the most
   common producer of them and it does not use `git rm`.

## Acceptance

- Archiving a todo and committing both halves by pathspec exits 0 from `foreign-hunk-check.sh` with
  no `--force` and no hand-reasoning about which failure is real.
- A path with both added and removed lines still reports foreign hunks exactly as it does today, and
  the new self-test proves both directions rather than only the fixed one.
- `skills/commit/SKILL.md` step 8 no longer describes the exclusion as `git rm`-only.

## Notes

The caller's workaround today is to notice that the only non-clean path is the deleted half, confirm
it is a pure deletion with `git diff HEAD --summary -- <path>` and `git diff HEAD -- <path> | grep -c
'^+[^+]'` returning 0, then proceed. That is correct but it is reasoning a script should not require,
and it only stays safe while the caller actually performs it rather than assuming.
