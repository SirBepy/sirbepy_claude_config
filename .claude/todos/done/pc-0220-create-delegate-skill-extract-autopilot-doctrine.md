<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Create /delegate skill (interactive orchestrator mode) + extract shared delegation doctrine out of /autopilot

**Type:** skill-improvement

## Goal

A new user-invocable skill **/delegate** that puts the MAIN agent into interactive
orchestrator mode for the whole session, plus a shared doctrine file both /delegate and
/autopilot import, so the delegation rules live in exactly one place. Designed 2026-07-22 in a
Fibo session with Joe (rated 8/10 there; the two "-> 9/10" lifts below are part of the spec).

## Context

Joe wants long build sessions to run as: he and the main agent (typically Fable) talk ideas
through in the main thread; the main agent NEVER writes code and barely reads it - subagents do
all building and all broad reading. /autopilot already contains much of the needed delegation
doctrine, but bundled with AFK-only behavior (auto-answering questions, blocker logs, grinding
without the dev). The differences:

- /autopilot: dev is AFK -> never block, auto-answer nested skills' questions, log blockers.
- /delegate: dev is PRESENT -> genuine forks become AskUserQuestion cards BEFORE dispatch;
  ideas are discussed in the main thread; nothing is auto-answered.

Shared substance (the doctrine to extract): subagent dispatch discipline and the 90/10 rule.
First use is queued: the Fibo worktree has a handoff todo (22, "bootstrap the v2 frontend
shell") whose session will start with /pickup and then /delegate - so this skill should exist
before that session starts.

## Approach

1. Create `~/.claude/refs/delegation-doctrine.md` with the shared rules:
   - **90/10 rule**: subagents do all building and all broad/multi-file reading; the main agent
     keeps SURGICAL rights - a targeted read of ~a few dozen lines, or a trivial one-line fix,
     when a subagent round-trip would cost more than doing it directly. Main agent never does
     feature-sized edits itself.
   - Dispatch discipline (dedupe with, and cross-reference, the existing global CLAUDE.md
     "Subagent model" section rather than contradicting it): every dispatch passes
     model:'sonnet'; escalate above sonnet only per the existing escalation triggers; scouts
     produce condensed SPEC PACKS (exact contracts, file:line pointers) before builders run;
     every builder prompt embeds its verify floor (project fast checks) and the verbatim
     "Stage your changes but do NOT commit..." line; reports come back as conclusions +
     evidence, never raw dumps.
   - Quality tells for distrusting a report (suspiciously clean, contradicts other evidence,
     zero findings on a big diff) -> targeted re-check or solo higher-tier verifier.
2. Create the skill `~/.claude-personal/skills/delegate/SKILL.md` (same home as the other
   personal skills - pickup/handoff/rate-it live in `~/.claude-personal/skills/`): triggers on
   /delegate only; on invocation the session ADOPTS the doctrine file for its whole remainder,
   plus the interactive layer: forks surfaced as question cards (per global question rules)
   before any dispatch that depends on them; main-thread discussion stays with the dev; no
   auto-answering. Keep the skill file thin - it should mostly point at the doctrine file.
3. Refactor `/autopilot`'s SKILL.md: remove the text now duplicated by the doctrine file and
   replace with an explicit "follow ~/.claude/refs/delegation-doctrine.md" import, keeping only
   the AFK-specific layer (auto-answer policy, blocker logging to .for_bepy/autopilot-logs/,
   grind-to-finish, READY_TO_COMMIT marker mechanics). Behavior must remain identical for
   autopilot runs - this is extraction, not redesign.
4. Check `~/.claude/refs/process-hygiene.md` and the global CLAUDE.md subagent section for
   overlap; link rather than copy.
5. Sanity pass: read both resulting SKILL.md files end-to-end; confirm no rule now exists in
   two places with different wording.

## Acceptance

- /delegate invocable; a session that runs it demonstrably dispatches builders/scouts instead
  of editing code in the main thread, and asks fork questions interactively.
- /autopilot still fully specified (nothing lost in extraction) but with the shared parts
  imported from the doctrine file.
- No contradiction between doctrine file, global CLAUDE.md subagent rules, and either skill.

## Notes

- Naming settled by Joe: **/delegate** (over /conduct) - clearer.
- The Fibo handoff todo that depends on this: Fibo worktree
  `items-registry-purchases-split/.claude/todos/22-handoff-v2-frontend-orchestrator-bootstrap.md`.
