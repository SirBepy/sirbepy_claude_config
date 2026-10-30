<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1258 holds different defects from the 2026-10-28 review; 1065, 1261, 0070, 0208 are other surfaces -->
# /gate-chat and /respawn hand-off prose gaps from the 2026-10-30 push review

**Type:** skill-improvement
**Origin:** ai
**Summary:** Close four gaps where the push gate hand-off or the respawn hand-off tells a fresh chat to do something it cannot do as written.

## Goal

The gate chat and the respawn successor get every instruction they need, and every attended push path goes through `/gate-chat`.

## Context

Found by the 2026-10-30 `/review-unpushed` pass (commits 4d13e60 and da12f82), cited from the reviewer's report, not re-read by the filing session:

1. `skills/commit/SKILL.md` Push rule ("nothing to commit, N ahead" path, ~line 185) runs the sweep, transcript check and gate directly and never mentions step 1c or `/gate-chat`, contradicting "every attended push" in the Gate hand-off section and `skills/gate-chat/SKILL.md:5`.
2. `skills/gate-chat/SKILL.md:22`: the `/release` hand-off prompt says "4b only under /release" but never points the child at `skills/release/SKILL.md` section 4b; the child does not load `/release`, so it lacks the bump exit-code handling and the `--reason "version bump after gate"` mark.
3. `skills/gate-chat/SKILL.md:10,20`: uses `@{u}..HEAD` with no guard for a branch that has no upstream; only `/release` handles that case.
4. `skills/respawn/SKILL.md:214-216` and `skills/loop-todos/SKILL.md:168`: loop-todos uses the New-work template, which requires "Joe's words for it, verbatim". An automatic caller has no such words, so the successor gets an empty or invented quote.

## Approach

1. Make the Push rule's N-ahead path go through step 1c like the commit path (or state explicitly that it is exempt, and why).
2. Add "read `skills/release/SKILL.md` section 4b" to the release hand-off prompt.
3. Add a no-upstream check before the range is used, offering `git push -u origin <branch>` as the Push rule already does.
4. Mark the verbatim field "Joe-invoked only" and give automatic callers a substitute line (the caller skill's name and its trigger).

## Acceptance

- `skills/release/test_pipeline_order.py` still passes.
- Each of the four citations above reads correctly when followed literally by a fresh chat.
