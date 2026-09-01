<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=a0fa7504 -->
<!-- duplicate-checked -->
# /commit needs a mechanical foreign-hunk check for shared-worktree repos

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/commit` step 8's working-tree diff check a mechanical helper for repos where several
Conductor sessions share ONE working tree, so "are any of these hunks someone else's?" stops being
a per-file manual read.

## Context

Hit repeatedly on 2026-08-26 in `c:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar`, which
runs 3-4 concurrent Conductor sessions against a single checkout.

`/commit` step 8 already says to run `git diff` per pathspec entry and account for every hunk. That
rule is correct and it caught a real collision: three files (`chat-event-handler.ts`,
`chat-pagination.ts`, `chat-transforms.ts`) held another session's in-flight AUQ work interleaved
with mine, and a pathspec commit would have swept in their unfinished code (2 red view specs at the
time). But executing it meant reading every diff by eye, three separate times across one session,
and the judgement "is this hunk mine?" rests entirely on recall of what was edited this session.

Two things a helper could do mechanically:
1. Print, per pathspec file, whether its diff hunks overlap the line ranges this session actually
   edited (the harness knows which files/edits this session made).
2. Flag the sub-hunk case explicitly - when a foreign hunk sits INSIDE the same `@@` hunk as one of
   yours, `git apply --cached` cannot split it, so the only safe orders are "peer commits first" or
   "reconstruct HEAD + your delta as a blob". Today that has to be worked out from scratch each
   time, under time pressure, with a peer actively editing.

Also worth encoding: a peer's commit is NOT a guarantee your hunks landed. In that same session the
peer's commit came back with two of my files restored from HEAD, silently dropping my edits from
disk - see the project memory `project_peer_commit_can_revert_your_hunks`.

## Approach

1. Add a small script under `skills/commit/` (sibling to `prefilter-gate.sh`) that takes the
   pathspec and prints a per-file verdict: clean / foreign-hunks-present / foreign-hunks-inside-your-hunk.
2. Wire it into step 8's precondition list for repos detected as shared-worktree (several live
   sessions with the same `worktree` in the Conductor peer list, or simply always - the check is
   cheap and harmless in a single-session repo).
3. Document the "peer commits first, then VERIFY your lines are in HEAD" ordering in
   `skills/commit/edge-cases.md` next to the existing split-a-file section.

## Acceptance

Running the helper against a tree where a peer has hunks in one of your pathspec files names that
file and says whether the overlap is sub-hunk, without reading any diff by hand.
