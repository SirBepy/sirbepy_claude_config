<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The commit guard fails open on a git commit with no explicit pathspec

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide, and then either close or deliberately document, the gap todo 844's fix left behind: a bare
`git commit -m "x"` with no `-- <paths>` is not gate-checked at all.

## Context

Filed 2026-09-01 by the `/mega-todos` builder that closed todo 844 (commit `32fabed`), as an
out-of-scope finding it surfaced rather than silently resolved.

844 made `hooks/commit-guard.py` reject a commit chained after a gate with `;`, while leaving the
prescribed `gate && git commit` form allowed. But the gate check keys off the pathspec the commit
names. A commit relying on whatever is already staged has no pathspec to key off, so it fails open.

The builder's stated reason for not closing it: determining "the staged pathspec" from inside a
hook means querying the shared git index, which in this repo can hold another concurrent session's
staged work. Reading that index to decide whether to block would make the guard's verdict depend
on a peer's uncommitted state, which is worse than the gap it closes.

This is narrow: it only bites when a caller has already violated the project's own "never
`git commit -a`, always name the pathspec" rule in `/commit` step 8. That makes it a
defence-in-depth question, not an active defect, which is why it is filed as its own decision
rather than reopened against 844.

Duplicate check, 2026-09-01: the guard flagged 852, 256, 243, 245 and 75 on shared vocabulary.
852 is about `/commit fold` recommitting riding commits by pathspec and absorbing later hunks, a
different mechanism in a different file; the rest share only the words "commit" and "guard". Read
and dismissed, not folded.

## Approach

1. Read `hooks/commit-guard.py` as it stands after `32fabed` and confirm the gap by probing a bare
   `git commit -m "x"` against the hook directly, not by inspection.
2. Weigh three options and pick one, naming the tradeoff:
   - Block any `git commit` that names no pathspec outright. Simplest and strictest; would need a
     carve-out for `--amend` and for the archival commits `/commit` itself makes.
   - Leave it open and document the gap in `skills/commit/SKILL.md` step 8 so a reader knows the
     hook does not cover this form.
   - Something narrower, e.g. block only when the command also lacks `--amend` and the repo has a
     shared git-common-dir.
3. Whatever is chosen, add a test to `hooks/test_commit_guard.py` pinning the decided behaviour, so
   a later change cannot silently flip it.

## Acceptance

- The chosen behaviour is implemented and pinned by a test in `hooks/test_commit_guard.py`.
- The prescribed `gate && git commit -- <paths>` form still passes, proven by the existing tests.
- If the decision is to leave it open, `skills/commit/SKILL.md` step 8 says so explicitly.
- `python ci/run_all.py` exits 0.
