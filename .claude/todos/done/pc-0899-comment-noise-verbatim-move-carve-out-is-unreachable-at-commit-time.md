<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `done/258`'s verbatim-move carve-out exists only as prose, so the commit hook still forces the trim

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the comment-noise carve-out for pure code moves reachable at COMMIT time, so a builder that
correctly identifies a verbatim move can actually commit it instead of being forced to reword
documentation to get past the gate.

## Context

Hit live on 2026-09-03 during a `/mega-todos` run in `claude_usage_in_taskbar`, todo 847 (splitting
`tool-strip-screenshots.ts` and `tool-strip-subagents.ts` out of `tool-strip.ts`).

`done/258-comment-prefilter-blind-to-pure-code-moves.md` closed by writing the carve-out into the
rule text: `skills/mega-todos/SKILL.md`'s injected commit block and `refs/builder-preamble.md` both
now say a comment-noise hit on lines that are a VERBATIM MOVE from another file in the same commit
is expected and must NOT be trimmed, confirmed via `git show HEAD:<old-file>`.

That instruction is real but unenforceable. The builder did exactly what it says:

> tool-strip-screenshots.ts's mounting docblock and its "Every call for this key..." inline comment
> were byte-identical verbatim moves from tool-strip.ts's HEAD (confirmed via git show
> HEAD:src/shared/chat/tool-strip.ts), so per the dispatch's own instructions they should NOT have
> been trimmed

and then could not commit, because the commit-time `PreToolUse` hook re-runs the same mechanical
`prefilter-gate.sh` with zero awareness of the exemption and hard-blocks any exit 1. A subagent has
no bypass. It trimmed both comments purely to get the commit through, which is the exact outcome
`done/258` was filed to prevent, and it flagged the gap in its report rather than hiding it.

This is structurally the same defect as `778-em-dash-exempt-marker-is-honored-at-write-time-but-not-
at-commit-time.md`: an exemption taught to one layer and not to the layer that actually gates. The
difference is that `778`'s exemption at least has a marker to honor. This one has no mechanism at
all, only prose, so there is nothing for the hook to check even in principle.

## Approach

1. Decide the mechanism first, because the carve-out needs to be machine-checkable and today it is
   not. Two candidates, pick one deliberately:
   - **Compute it.** Teach `skills/commit/comment-noise.sh` (or `prefilter-gate.sh`) to detect a
     verbatim move itself: for each flagged added comment line, check whether that exact line exists
     in `git show HEAD:<some deleted/shrunk file in the same diff>`. Expensive but needs no marker
     and cannot be abused, since the line must genuinely already be in HEAD.
   - **Mark it.** A `<!-- comment-move-exempt -->` style marker, following `778`'s pattern. Cheaper,
     but a marker on source files is a repo-wide escape hatch on a rule CLAUDE.md states firmly, and
     `778`'s own Approach item 3 already argued against exactly that for em dashes.
   Recommendation: compute it. The move case is mechanically decidable from the diff, which is what
   makes it different from the em-dash case.
2. Whichever is chosen, the gate and the hook must agree. Verify against the real hook path, not
   just by running `prefilter-gate.sh` by hand: the whole defect here is that the two disagree.
3. Until it lands, say so in the rule text rather than leaving builders to discover it mid-commit.
   `skills/mega-todos/SKILL.md` and `refs/builder-preamble.md` currently promise an exemption that
   the gate will not grant, which is worse than promising nothing.

## Acceptance

- A commit whose only comment-noise hits are byte-identical lines already present in HEAD under a
  different path passes the gate AND the commit-time hook, with no rewording.
- A commit with a newly authored over-cap comment block is still flagged, in the same run.
- A commit mixing both is flagged for the new block only.
- The rule text in `skills/mega-todos/SKILL.md` and `refs/builder-preamble.md` matches what the gate
  actually does.

## Notes

- Real cost so far: two verbatim-moved comments in `claude_usage_in_taskbar` commit `9a63324f` were
  reworded below the cap to land the commit. No constraint was lost this time (the builder checked),
  but `done/258` documented three constraint-bearing clauses destroyed the same way, so the failure
  mode is proven, not hypothetical.
- Sibling defect, same shape, different rule: `778`.
- Ancestor: `done/258`, which fixed the doctrine and not the gate.
- Completed in the mega-todos wave 1 run, commits ecee356 + aace76f: comment-noise.sh now builds a haystack of every HEAD line across every file the diff touches and excludes any flagged comment line byte-identical to a HEAD line under a different path, so a verbatim move never reaches the report. Covered by three new cases in test_commit_guard.py's real-repo block. The stale prose in mega-todos/SKILL.md and builder-preamble.md was updated by the orchestrator afterwards, since both sat outside the builder's lane. Todo 904 was folded in as the dedupe loser.
