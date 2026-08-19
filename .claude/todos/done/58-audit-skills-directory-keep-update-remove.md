<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=7, reconfirm-count=3, content-hash=1ec3adee -->
# Full audit pass over skills/ deciding keep, update, or remove per skill

**Type:** task
**Origin:** dev

## Goal

Run a full audit pass over every skill under `C:\Users\tecno\.claude\skills\`, producing an explicit
keep / update / remove verdict for each one.

## Context

A prior audit ran 2026-08-01: 12 skills deleted, 3 merges, and it spawned the todos in the 29-48 id
range. This is the follow-up pass, not a repeat - it should start from what that audit left rather
than re-auditing everything from zero.

Concrete trigger: this entire backlog is 100% `ai`-origin. A single `/auto-do-todos` re-verification
run on 2026-08-08 found five todos (09, 14, 18, 32, 54) whose premise was already dead or drifted
against the current tree. That prompted the dev to want the skills surface itself pruned, verbatim:
"we will have to revisit a lot of skills soon and see what should be removed/updated".

## Approach

Backlog todos deliberately BLOCKED on this audit, because each wants to add brand new skill surface
and adding them before the prune would immediately outdate it. **Re-verified 2026-08-17** - the list
this todo was written with has half rotted, so take this version, not the original:

- **11** (`/orphan-audit`) - still live, still blocked.
- **30** (`/story-shot`) - still live, still blocked.
- **362** (render-and-diff a built screen against its design tile) - filed 2026-08-17, NOT formally
  parked because Joe was never asked. Same new-skill-surface shape as 11 and 30. Rule on it here.
- **44** (shared Playwright measure + screenshot helper) - **DONE**, no longer blocked or pending.
- **63** (`/screenshot` multi-frame local build mode) - **DONE** 2026-08-13, authorized by Joe ahead
  of this audit on the reasoning that it extended an existing skill rather than adding one. That
  reasoning is the precedent to reuse when deciding whether something is surface-growing at all.

The audit should rule on 11, 30 and 362 explicitly as part of its output, not leave them pending.

## Acceptance

- Every skill under `skills/` has an explicit keep / update / remove verdict.
- Todos 11, 30, and 362 are each either unblocked (with a stated reason) or closed.

## Notes

- Completed 2026-08-18. 83 skills triaged, 6 independent reviewers over 3 contested clusters. Zero removals - the tree was already clean. 13 skills flagged slash-only, cutting always-on description budget 10445 to 5892 chars (43.6%). 4 correctness fixes. Rulings: 11 unblocked as a script, 30 unblocked as a fibo-local skill, 362 kept separate and folded into the /test-and-/e2e direction. Full record in skills/AUDIT-2026-08-18.md. NOT done: the 15 high-usage core skills got a mechanical pass only, no dedicated improvement reviewer.

## Open questions

Answered 2026-08-13. No open question remains, only a scheduling decision.

Asked on 2026-08-13 how the audit should run. Joe's answer, verbatim: "this is meant to be a whole
session kind of thing, so skip this for now." So it is not a question any more, it is a job waiting
for a session of its own. Do NOT open it as a side quest inside another run.

Two things a future run should know before starting it:

- The count is **83 directories, 1101 files, 680 tracked**, re-enumerated 2026-08-17. It was 76 /
  669 / 664 on 2026-08-13 and ~78 when this todo was first written, so the surface is growing while
  the audit waits. Note the 421-file gap between files-on-disk and files-tracked: that is untracked
  runtime spill (Playwright profiles and similar) sitting inside `skills/`, and deciding what to do
  with it is arguably part of this pass.
- **12 of those are vendored**, not hand-authored (the 11 Cloudflare-family skills plus
  `impeccable`), all added in one commit, `4cc2977`. They are documented in `skills/VENDORED.md`
  with their patch status. Only ONE carries a local patch. The audit should judge those 12 on
  "do we still want this installed" rather than on quality, since their content is upstream's.

Blocks 11, 30 and 362, all of which stay parked until this runs.
