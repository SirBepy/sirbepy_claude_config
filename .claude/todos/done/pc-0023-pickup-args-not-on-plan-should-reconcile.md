<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=a3cfd115 -->
# /pickup: free-text args that don't match any PLAN.md id should be reconciled, not silently substituted

**Type:** skill-improvement

## Goal

Harden `/pickup`'s Step 1 (Select) so that when the invocation carries free-text args instead of
a bare id, and those args don't correspond to anything on `PLAN.md`, the skill surfaces that
mismatch instead of letting the executor quietly treat the free text as if it were the task.

## Context

2026-07-20 session: `/pickup` was invoked with args `"to be clear, before we make any changes, i
first need you to figure out what the ui looks like, and then give me /mockup of what it would
look like"` — clearly a natural-language instruction, not a todo id. `PLAN.md` at the time had
exactly one line, unrelated to the args (`120 - PR screenshots + Slack merge announcements`).

The skill's Step 1 only documents two cases: "explicit `<id>` arg was given" or "no explicit id —
take the first unclaimed PLAN.md line." Free-text args that are neither an id nor blank fall
through a gap the skill doesn't address. The executing session filled that gap by inferring a
target from the current git branch name (`feature/test-shopping-cart-revamp`) and a project
memory about a prior shopping-cart session, then spent a full turn (supervised-run bring-up,
Playwright screenshots, a spec-search subagent, kicking off `/brainstorm`) on that inferred task
before the dev caught it: *"where did you get that this is what I wanted?"* Turned out there was
no todo backing the assumption at all — the closest match was `127-split-test-shopping-cart-page`,
whose actual (then-current) content was an unrelated file-split task, not what got worked on.

This is the same failure class as the `feedback-verify-frame-not-inherited-interpretation`
memory (confirm the literal target before building), but specific to `/pickup`: the skill's own
selection algorithm has no branch for "args look like a fresh instruction, not a lane reference."

## Approach

Edit `~/.claude/skills/pickup/SKILL.md` (or wherever this project's `/pickup` resolves to — seen
at `C:\Users\tecno\.claude-personal\skills\pickup` and `C:\Users\tecno\.claude-fibo\skills\pickup`
this session, so check both) Step 1 to add a third case: args given that are neither a bare id
nor empty →
- Check whether the args plausibly reference an existing backlog item (by slug/title match).
- If yes: confirm with the dev in one line before proceeding ("this looks like todo NN — <title>,
  continuing with that?").
- If no match at all: do NOT infer a target from git branch, memory, or file state. State plainly
  that the args don't correspond to any PLAN.md/backlog item and ask what to do (start a fresh
  `/create-todo`? point at a specific id? something else?) via `AskUserQuestion`.

## Acceptance

- A `/pickup` invocation with free-text args that don't match any backlog item no longer results
  in the executor silently picking its own interpretation and doing work before checking.
- Bare-id and empty-args cases (already documented) are unaffected.

## Notes

The dev's actual want, once surfaced, turned out to be legitimate and valuable (a spec-vs-mockup
gap analysis on the shopping-cart flow, folded into `127` — see that file, now retitled "Close
shopping-cart mockup vs spec gaps"). This todo is about the process gap, not about the content
being wrong.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 132; renumbered to 23 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: added a third Step 1 case to `pickup/SKILL.md` for free-text args - slug/title match confirms in one line before proceeding; no match states that plainly and asks via `AskUserQuestion` instead of inferring from branch/memory/file state. Bare-id and empty-args cases untouched.
