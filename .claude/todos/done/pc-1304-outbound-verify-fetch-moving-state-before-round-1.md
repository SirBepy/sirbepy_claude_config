<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1302 is about the guard blocking a GET loop; PLAN.md has no round-1 freshness item. Not a duplicate. -->
# outbound-verify: make the "re-check moving state before round 1" line a step, not a tip

**Type:** skill-improvement
**Origin:** ai
**Summary:** `refs/outbound-verify.md` says a newly merged PR makes text stale and to re-check before round 1, but nothing in `/ticket` or the ref makes the session fetch the repos the draft talks about; a whole round of 3 verifiers was wasted on 2026-11-03 because of it.

## Why

zng-app "Biller Groups ticket decision" chat, 2026-11-03. The spawn brief listed "facts verified by the hub chat at ~17:30 local" including "sc-56598 is NOT merged". The chat drafted the zng-app ticket on that, dispatched 3 verifiers, and all 3 FAILed on the same point: PRs 970 and 971 had merged into zng-api develop at 17:09 local (`git log origin/develop` after a fetch). The verifiers found it because the template tells THEM to `git fetch --quiet` first; the main session never did. One round, 3 sonnet agents, about 280k tokens, for a fact one `git fetch` would have caught.

## Goal

Before round 1 of any outbound verify on text that names a repo state, branch, PR or ticket state, the main session has fetched every repo the draft or its pointers name and re-read the Shortcut state of every ticket the draft cites, in the same turn, and the dispatch prompt carries the resulting HEAD shas.

## Approach

1. In `refs/outbound-verify.md` "Procedure" step 1 (Freeze the text), add a numbered sub-step: `git fetch --quiet` in each repo the pointers name and record `origin/<branch>` sha; GET each cited story's `workflow_state_id`; put both in the Pointers line. Move the existing "A newly merged PR or ticket makes text stale" tip from "Keeping the verify loop short" into that step.
2. In `skills/ticket/SKILL.md` Create step 6, say the same in one line, pointing at the ref.
3. Consider a tiny helper `skills/ticket/scripts/freshness.ps1 -Repos a,b -Stories 1,2` that prints the sha and state lines ready to paste into the Pointers field, so the step costs one call.

## Acceptance

- The ref's step 1 names the fetch and the state re-read as required, with the 2026-11-03 incident as the why.
- A session following `/ticket` cannot reach the dispatch without having printed the shas and states it will hand the verifiers.

## Verify

- [ ] `grep -n "git fetch" ~/.claude/refs/outbound-verify.md` shows it under step 1, not only inside the template
- [ ] `grep -n "round 1" ~/.claude/skills/ticket/SKILL.md`

## Notes

- Filed by `/close` of the zng-app chat on 2026-11-03. Sibling finding, same session: the verifier template's pointer paths for zng-app were stale (`biller_slug_landing_screen.dart` lives under `lib/ui/loan_application/biller_landing/`, `add_account_screen.dart` under `lib/ui/loan_request/my_bill/`); three verifiers each spent a tool call rediscovering them. A `git ls-files | grep` before dispatch would have fixed that too, same step.
- Built: refs/outbound-verify.md Procedure step 1 now requires the fetch and ticket-state refresh before round 1 (2026-11-03 incident as the why); skills/ticket/scripts/freshness.py prints the dated shas, story states and real tracked paths (--find); verify_prompt.py refuses a spec without '## Freshness'; skills/ticket/SKILL.md Create step 6 says so in one line. Tests: test_freshness.py (real throwaway repos, stubbed Shortcut API), test_verify_prompt.py (red-checked). The skill text cannot prove the session ran freshness.py; the required spec section is the nudge.
