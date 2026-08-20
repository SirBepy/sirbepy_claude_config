<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Every hook is global, so a guard meant for subagents also fires on the main thread

**Type:** task
**Origin:** ai

## Goal

Use per-agent `hooks:` and `permissionMode:` in subagent frontmatter, so a guard that only makes sense
for dispatched work stops constraining the main session.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

All 41 hooks are wired globally in `settings.json`, so every guard applies to every context: the main
interactive thread, every dispatched subagent, and unattended runs alike. Several existing guards are
conceptually subagent-only and are global purely because that is the only wiring available today:

- `dispatch-preamble-guard.py` blocks a dispatch missing preamble markers. Only meaningful when the
  main agent dispatches, and it has already been a friction point this session, firing on a read-only
  research scout that needed the `READ-ONLY DISPATCH` opt-out.
- The delegation doctrine's whole ban list (no `git stash`/`reset`/`checkout` on paths you do not own,
  no `git add -A`, no `run_in_background`, no glob cleanup near `hooks/.commit-marker-*`) is enforced
  by **prose in the dispatch prompt**, not by hooks, precisely because those rules must not apply to
  the dev's own main-thread work. Per-agent hooks are the mechanism that prose is standing in for.

Reference: `repos/DazzleML_dazzle-claude-code-config/dotclaude/agents/tester-unbounded.md:6-12`. That
agent's frontmatter carries `permissionMode: acceptEdits` plus a `hooks.PreToolUse` block naming
`tester-unbounded-guard.py`. The hook fires only while that agent is active.

This is the highest-leverage unused config surface found, because it turns a documented-but-unenforced
rule set into an enforced one without touching the main thread. It also connects to two live items:
todo 426 (unused hook events and JSON fields) and the fact that **this repo has exactly one agent
definition** (`agents/` contains 1 file), so there is almost no per-agent surface in use at all.

The uncertainty to resolve first: subagents are dispatched here via the `Agent` tool with inline
prompts, not via named agent definitions. Per-agent frontmatter hooks attach to **named agent types**.
So this may require defining real agent types (a `builder`, a `scout`) to hang hooks on, which is a
bigger change than adding a frontmatter block. That is the thing to establish before building.

## Approach

1. Verify the mechanism in this harness version before designing around it: does an `agents/*.md`
   frontmatter `hooks:` block actually fire, and does it fire for `Agent`-tool dispatches that name
   that agent type? Test with a trivial hook that just logs. **Do not migrate any guard on the
   assumption this works.**
2. Establish whether inline-prompt dispatches can carry per-agent hooks at all, or whether named agent
   types are a prerequisite. This determines the size of the whole todo. Report the answer either way.
3. If named types are required, decide whether that is worth it. Defining `builder` and `scout` agent
   types would also let the builder preamble live in the agent definition instead of being pasted into
   every dispatch prompt, which is a real second benefit and arguably the bigger one. Weigh it
   explicitly rather than treating hooks as the only payoff.
4. Migrate exactly one guard as a pilot: `dispatch-preamble-guard.py` is the wrong first choice (it
   fires on the dispatcher, not the dispatchee). Better pilot: a guard enforcing one item from the
   doctrine's ban list, scoped to a builder agent type, where the main thread is provably unaffected.
5. Confirm both directions. The guard must fire inside the scoped agent AND must not fire on the main
   thread. Checking only the first half is how a global hook gets shipped by accident.

## Acceptance

- The mechanism is proven with a real firing and a real non-firing, not inferred from documentation.
- A stated answer on whether named agent types are a prerequisite.
- One guard scoped to one agent type, verified to fire there and verified NOT to fire on the main
  thread.
- No existing global hook's behavior changes. All 13 hook tests still pass, real output pasted.
- If named agent types get defined, the builder-preamble consolidation is at least assessed, since
  that is the larger win hiding behind this.

## Notes

The prize here is not tidiness. It is that `refs/delegation-doctrine.md` and
`refs/builder-preamble.md` currently enforce their rules by asking the model to have read them, and
the harvest's clearest lesson is that prose-only rules fail repeatedly here. This is the mechanism
that could make the doctrine's ban list real.

Do not migrate the whole ban list at once. One guard, both directions verified, then decide.
