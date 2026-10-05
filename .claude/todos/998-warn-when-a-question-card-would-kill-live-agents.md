<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=76589161 -->
<!-- duplicate-checked: the behaviour itself is already recorded as a zng-app project memory (reference_question_card_answer_kills_background_agents). This todo is about the missing MECHANICAL guard, not about documenting the behaviour again. -->
# 998 - Warn when a question card is about to kill live background agents

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-23

## Goal

Make it impossible to silently destroy in-flight background agents by firing a question card, or at
minimum make the cost visible at the moment it is about to be paid.

## Context

Answering an `AskUserQuestion` / `ask_user_question` card kills every background agent the session
has in flight. This is recorded as a zng-app project memory,
`reference_question_card_answer_kills_background_agents`, whose own guidance is "dispatch after the
answer".

It was violated anyway on 2026-09-23, in a zng-app session that had that memory loaded. The session
dispatched 5 background analysis agents, then fired two question cards. All 5 died with nothing
written to disk. They were relaunched and the work was redone, costing roughly 5 agent-runs and
several minutes.

The failure mode is what makes it worth a guard rather than a reminder:

- The agents die **silently**. No error, no notification. The session only learns by checking
  `ListAgents` or finding empty output files.
- The rule lives in memory, which is advisory prose. Nothing sits between the intent and the loss.
- The two actions are naturally separated by several turns, so "remember the rule" has to survive
  exactly the gap where attention is elsewhere.

This is the same shape as the rules that already earned hooks: knowing the rule is not the
mechanism, and the failure is invisible rather than loud.

## Approach

1. Establish first whether a `PreToolUse` hook on the question tool can see live agent state at all.
   The payload carries `session_id`; whether anything exposes that session's running background
   agents is the open question and decides the whole design. Probe it, do not assume.
2. If it can: a `PreToolUse` hook on `AskUserQuestion` and `mcp__cc_conductor__ask_user_question`
   that, when background agents are live, denies once with a message naming how many will die and
   telling the caller to either wait or accept the loss deliberately. A deny-once-then-allow shape
   fits better than a hard block, since sometimes the question genuinely matters more than the
   agents.
3. If a hook cannot see agent state: do not build a guesswork version. Fall back to adding the
   constraint to `refs/delegation-doctrine.md`'s dispatch discipline section, where an orchestrator
   reads it while writing dispatches, rather than leaving it only in one project's memory. Record
   the negative result here so nobody re-probes it.
4. Either way, generalise the memory out of zng-app. The behaviour is harness-level, not project
   level, so it belongs in the vault or in the doctrine, not in one project's store.

## Acceptance

- A probe result written down either way: the hook payload either can or cannot see live agents,
  with the evidence.
- If built: firing a question card with agents live produces a visible warning, demonstrated once.
- If not built: the constraint is in the doctrine rather than only in a zng-app memory.
