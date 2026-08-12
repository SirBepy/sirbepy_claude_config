<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=1ec3adee -->
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

Three backlog todos are deliberately BLOCKED on this audit, because each wants to add a brand new
skill, and adding them before the prune would immediately outdate it:

- **11** (`/orphan-audit`)
- **30** (`/story-shot`)
- **44** (a shared Playwright measure + screenshot helper)

The audit should rule on all three explicitly as part of its output, not leave them pending. Note
that 44 is arguably surface-reducing rather than surface-growing, since it consolidates duplicated
logic that already exists in `/screenshot` and `/mockup` rather than adding a genuinely new
capability - weigh it differently from 11 and 30 when deciding whether to unblock it ahead of, or
independent of, the rest of the sweep.

## Acceptance

- Every skill under `skills/` has an explicit keep / update / remove verdict.
- Todos 11, 30, and 44 are each either unblocked (with a stated reason) or closed.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] [TOOLING] This audit is dev-origin and blocks 11, 30 and 63, but its whole deliverable is a keep/update/remove verdict over 78 skills, and executing the removals is your call, not Claude's. How should it run? Options: (a) Claude runs the audit read-only next session and hands back one keep/update/remove table, you approve removals in a single pass; (b) Claude runs it and auto-archives only skills with zero references anywhere in the tree, surfacing every judgement call; (c) skip the audit and unblock 11, 30 and 63 directly instead. Recommended: (a), because the 2026-08-01 audit already showed the removals are the part that needs your taste.

The /auto-do-todos run on 2026-08-12 deliberately did NOT start this. Its output is a proposal that needs your confirm either way, so starting it would have spent the run's remaining context without producing anything shippable.
