<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=9ec926ec -->
# /create-pr's comment-noise prefilter can't see the trims it just asked for

**Type:** skill-improvement

## Goal

Stop `/create-pr`'s comment-noise gate from reporting the same offenders after they have been fixed,
which reads as "the trim did nothing" and invites re-doing work.

## Context

Skill file: `~/.claude/skills/create-pr/SKILL.md`, the "Comment-noise check" section.

Its prefilter runs `git diff <base>..HEAD | awk ...`, i.e. **commit range only**. Step 2b then tells
the main agent to trim the offenders in the working tree. Re-running the prefilter at that point
produces byte-identical output, because the trims are not committed yet. Hit live on 2026-07-31
while preparing the review-unmapped sheet PR: 12 files flagged, ~10 blocks trimmed, prefilter output
unchanged, and the only way to tell the difference was `git diff` on the working tree.

Second, smaller issue found the same run: the awk in the skill file contains `substr(worktree,7)` and
`substr(worktree,2)` where it means `substr($0,7)` / `substr($0,2)`. `worktree` is an unset variable,
so the snippet as written cannot work verbatim - it has to be repaired by hand every time.

## Approach

1. Fix the two `substr(worktree,...)` typos to `substr($0,...)`.
2. Make the range explicit and correct: diff `<base>...HEAD` PLUS the working tree, e.g. run the
   prefilter over `git diff <base>` (which includes uncommitted changes) rather than
   `git diff <base>..HEAD`, or run it twice and report the working-tree result as the live one.
3. Add one line to step 2b: after trimming, re-run against the WORKING TREE, not the commit range.
4. Consider stating the cap in delimiter-inclusive terms, since that is the part people get wrong:
   4 lines includes the `/**` and `*/` lines, so a JSDoc gets about two content lines.

## Acceptance

- The snippet in the skill runs verbatim, no hand-repair.
- After trimming comments but before committing, re-running the check reports the reduced set.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 184; renumbered to 38 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: Awk `$0` typo was already fixed in a prior pass (verified, no `substr(worktree,...)` remains). Fixed the remaining half: range-mode now runs `git diff <base>` (working tree included) instead of `<base>..HEAD`, with a one-line note in `comment-noise.md` explaining why, so a re-run after trimming reflects the trim. Did not touch `create-pr/SKILL.md` - comment-noise.md stays the single source of truth.
