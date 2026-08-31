<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for baseline / worktree / embed list: only done/391 (the parent), no live match. -->
# delegation-doctrine's builder-prompt embed list never mentions the baseline mechanism

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the orchestrator side of todo `391`'s fix real: `refs/delegation-doctrine.md`'s "Every builder
prompt embeds" list should name the baseline mechanism, so a dispatch that needs a before/after
measurement arrives carrying the number or the ordering instruction rather than leaving the builder
to improvise one.

## Context

Filed 2026-08-31 by the `/mega-todos` orchestrator, from todo `391`'s builder's own out-of-scope
report (commit `ccee012`).

`391` added a "Taking a baseline" clause to `refs/builder-preamble.md`, which is the BUILDER-facing
half: it tells a builder to take the baseline before editing and names `git worktree add` as the
fallback. `391`'s own Approach also asked for the ORCHESTRATOR-facing half, a mention in
`refs/delegation-doctrine.md`'s "Every builder prompt embeds" list, so the orchestrator knows to
supply a before/after number or an explicit ordering instruction when the task needs one.

That second half was deliberately out of scope for `391`'s dispatch: this run put
`refs/delegation-doctrine.md` in the same lane but assigned it to other todos, and `391`'s brief
scoped it to `builder-preamble.md` alone. The builder flagged the omission rather than silently
widening its own scope, which is the channel working as intended.

So this is a known, deliberate remainder, not a discovered defect.

## Approach

1. Read `done/391-builders-have-no-sanctioned-way-to-get-a-whole-tree-baseline.md` for the original
   Approach wording, and read the clause as it actually landed in `refs/builder-preamble.md`.
2. Add one line to `refs/delegation-doctrine.md`'s "Every builder prompt embeds" list: when a task's
   verification depends on a before/after comparison, the dispatch supplies the baseline value
   itself, or states the ordering (measure, then edit), rather than leaving the builder to obtain it.
3. Keep it to one line. That list is embedded reasoning the orchestrator reads on every dispatch, and
   the preamble already carries the builder-facing mechanics.

## Acceptance

- [ ] The embed list names the baseline responsibility in one line
- [ ] It points at `refs/builder-preamble.md`'s clause rather than restating the mechanics
- [ ] No new wording contradicts the clause `391` landed

## Notes

- Low worth on its own, roughly a 5: it closes a real half-finished item, but the builder-facing half
  is the one that prevents the `git stash` reach, and that already shipped.
