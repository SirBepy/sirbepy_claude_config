<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Handoff: build /test next, then continue the verb-first restructure

**Type:** task
**Origin:** dev

## Goal

Joe's stated end state, in his words on 2026-08-18: *"by the end of this, i will have more
confidence in all of my skills, theyll be tied to verbs as opposed to platforms, and ill be able to
tell you to do smth and youll infer what platform i want you to use."*

**The next concrete build is `/test`.** Joe chose the order himself: finish the outbound gate (done),
then `/test`. He wrapped the previous session at 51% context used, not because anything was blocked.

## Context

### What landed 2026-08-18, all pushed to origin/master

**Todo 58, the full skills audit.** 83 skills triaged, 6 independent reviewers over 3 contested
clusters, then 2 adversarial checkers over the result. **Nothing was deleted, merged or rewritten,
and that was the correct outcome** - reviewers verified 16 dormant skills against the live
filesystem and found none dead. What the audit actually bought was context budget: **13 skills
flagged `disable-model-invocation`, cutting the per-session description cost from 10,445 to 5,892
chars (43.6%)**. Full record in `skills/AUDIT-2026-08-18.md`. Do NOT re-audit.

**The shared outbound gate**, Joe's pick for the first restructure build:

- `refs/outbound-ground-check.md` - platform-agnostic ground check. Queries 1 and 3 (merged PRs,
  the claim at the tracked branch) were already platform-agnostic; only the tracker search differs.
- `hooks/linear-create-guard.py`, `hooks/linear-update-guard.py` - new.
- `hooks/shortcut-mutation-guard.py` - **moved** out of `skills/shortcut-create-ticket/hooks/`,
  where `/ticket` would have silently disarmed it.
- Updates are gated only when **claim-bearing** (name, description, comments). State moves and
  self-assign stay frictionless. Joe's explicit call, and it matches the ref's own narrow-hard-stops
  doctrine. Do not widen it without asking.

### Decisions already settled, do not re-litigate

- **11** unblocked as a SCRIPT, not a skill. **30** unblocked as a **fibo-local** skill. **362** kept
  separate from `flutter-e2e` rather than bolted into it.
- **The tree-wide "consolidate everything into routers" idea scored 3/10** across two rating panels
  (9 subagents). The DRY premise was falsified by measurement: remaining duplication across the
  ticket skills is roughly a 3-line warning repeated three times. **Do not revive it.**
- The narrow `/ticket` merge (create/update/pickup, platform looked up) scored 5/10 and IS worth
  doing, but for consistency-of-enforcement reasons, NOT for DRY. Joe's create/update/pickup split
  is better than todo 351's original all-eight shape: `priorities` and `done-audit` stay separate,
  since they are cross-ticket sweeps, not per-ticket operations.
- **Platform inference is fine** and Joe pushed back correctly on requiring an explicit platform
  argument. He means a deterministic repo-to-tracker lookup, not a model guess.
  `hooks/gh-account-switch.sh` already proves that pattern in this tree.
- **Obsidian is out of scope** for ticket work. Joe: *"obsidian isnt important at all... later when
  i need obsidian, i can ask an ai to add obsidian."*
- **`/respawn` is broken** (needs a `spawn_chat` MCP tool that does not exist). Joe: *"dw bout
  respawn yet... a new version will come out for claude_conductor and that should fix it."* Ignore it.

## Approach

1. **Build `/test`.** One verb, unit plus e2e, stack inferred rather than named. It is the smallest
   complete instance of the verb-first pattern and proves the shape before `/ticket` bets on it.
2. **Keep the explicit command and the automatic floor separate.** `/test` typed by Joe means unit
   plus e2e. The AUTOMATIC pre-done floor stays fast-checks-only. Blurring them makes every one-line
   edit expensive. See Notes for the unresolved half.
3. Then `/ticket`, per the split above, sitting on the gate that now exists.

## Acceptance

- `/test` runs the right suites for the detected stack without being told which stack.
- The automatic testing floor's behaviour is unchanged unless Joe explicitly decides otherwise.
- No new always-on description budget beyond what `/test` genuinely needs.

## Verify

- [ ] `git -C C:/Users/tecno/.claude status --short` - expect only other sessions' dirty files
- [ ] `git -C C:/Users/tecno/.claude log --oneline -8` - expect `97f2291` at or near HEAD
- [ ] `ls C:/Users/tecno/.claude/.claude/todos/.claims/` - expect empty
- [ ] `cd C:/Users/tecno/.claude/hooks; foreach ($t in Get-ChildItem -Filter "test_*.py") { python $t.FullName }` - expect 11 suites passing

## Notes

- **UNRESOLVED, and `/test` touches it:** Joe wants no tests by default, with a prompt instead. Two
  objections were raised and never answered. First, the floor is already **fast checks only** and
  e2e was excluded from it in the original commit `8d97b66` (2026-06-01), so the slow thing he wants
  gone was never in it. Second, "ask me if I want a test" fires after every task, which his own
  front-load rule forbids. Proposed instead: Claude SAYS when e2e looks worth it, he declines if he
  disagrees. **Get a decision before changing any default.**
- **`~/.claude/.env` had a UTF-8 BOM** that made `shortcut-mutation-guard.py` fail closed on every
  Shortcut mutation, silently, with "SHORTCUT_API_TOKEN not set in hook env". Fixed twice over: the
  loader now uses `utf-8-sig`, AND the BOM was stripped from the file (backup at `.env.bak`, 14 keys
  and all value lengths verified identical). `refs/shortcut-api.md:8` had already worked around it
  in the bash path with `sed`, which is why only the Python reader broke.
- **Still open from 375:** the `/linear` SKILL.md pointer to the ground check. Blocked twice because
  a concurrent session has uncommitted changes in that file. Enforcement does not depend on it - the
  guard's deny message names the ref.
- **Still open from 58:** the 15 high-usage core skills (`commit`, `close`, `code-check`,
  `supervised-run`, ...) got a mechanical pass only, never a dedicated improvement reviewer.
- Highest-value unrelated backlog item is **356**: `/commit`'s prefilters and `git commit` in one
  shell call have no gate, so a flagged diff can still land. It already happened once, in `8abd412`.
- Expect company in this repo. Several concurrent sessions were writing throughout; todos 370, 371,
  374 and the `respawn` skill all arrived mid-session from other chats. Commit strictly by pathspec.
- Done 2026-08-18. /test shipped at skills/test/SKILL.md - slash-only (zero always-on description budget), stack inferred from marker files (Flutter, Node/web, Rust/Tauri, Roblox/Luau, plus a scripts-repo fallback), e2e delegated to /flutter-e2e and /jest-lua rather than absorbed. Joe answered all three open decisions: floor stays fast-only but Claude now flags when e2e looks worth running (two new bullets in CLAUDE.md), all four stacks in v1, slash-only invocation. The /ticket half of this handoff was folded into todo 351, which now carries the settled create/update/pickup scope.
