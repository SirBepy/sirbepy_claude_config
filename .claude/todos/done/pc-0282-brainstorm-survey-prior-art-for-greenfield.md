<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=9, reconfirm-count=2, content-hash=f9268193 -->
# /brainstorm should survey prior art before designing a greenfield project

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a prior-art survey step to `/brainstorm` that fires when the target is a new standalone
project rather than a feature inside an existing codebase, so the first question asked is "does
this already exist for free?" instead of "what should we name it and how should we architect it?".

## Context

2026-08-12, `all_da_sheets` session. Joe invoked `/brainstorm` on an empty repo for a sheet-music
library and piano practice app. The skill's Phase 1 is "check the todos backlog, then explore
code" - on an empty repo that returns nothing, so the skill went straight to naming rounds and a
seven-question architecture card (storage backend, device targets, rendering pipeline, scraper
sources).

Joe then interrupted with: "also keep in mind that before we build anything, lets look up similar
products, primarily open source ones and free ones, look at what they have, myb they got
everything i need and then we dont gotta build nothing."

That research took four web searches and found two free Android apps already shipping the hardest
feature on the list (microphone-driven score following on acoustic piano) plus a $16 app covering
most of the rest. Joe's decision changed from "build it" to "test the existing apps for a week
first". Every architecture answer given before that point was premature - the storage question in
particular is meaningless if the answer is "use MobileSheets".

The failure is structural, not a lapse in judgment. `/brainstorm` step 1 infers context from the
codebase, and a greenfield repo has no codebase to infer from, so the step silently returns empty
and the skill proceeds as if context were complete.

## Approach

In `C:\Users\tecno\.claude\skills\brainstorm\SKILL.md`, extend step 1 (currently "Check the todos
backlog first, then explore code") with a greenfield branch:

- **Trigger:** the target is a new standalone project - empty or near-empty repo, no existing
  feature to extend, and the ask describes a product rather than a change. Not for features
  inside an existing codebase, where prior art is irrelevant.
- **Action:** before generating names or asking architecture questions, run a prior-art sweep for
  existing free and open-source solutions. Report what they already do, what they charge, what
  they run on, and specifically **which of the stated requirements are already met**.
- **Then ask the scope question first**, before anything else: does the dev still want to build,
  given what exists? Options along the lines of trial-the-existing-apps / build-only-the-unserved
  gap / build it all anyway. Everything downstream depends on that answer.
- Note in the skill that naming and architecture questions are WASTED tokens until the scope
  question is answered, which is exactly what happened here.

Delegation caveat: CLAUDE.md's execution-discipline section says multi-query web research goes to
a subagent so raw dumps stay out of main context. The Conductor harness in that session had a
standing "do not call the Agent tool unless the user requested it" instruction, so the research
ran inline and cost real context. Whatever wording lands should defer to CLAUDE.md rather than
hardcoding "dispatch a subagent", so it degrades correctly in harnesses that block subagents.

## Acceptance

- A `/brainstorm` on an empty repo surfaces existing free/open-source alternatives and asks the
  build-or-not scope question BEFORE any naming or architecture question.
- A `/brainstorm` on a feature inside an existing codebase behaves exactly as it does today - no
  new step, no extra questions, no added latency.
- The skill's gate-free character survives: this is one extra question in the existing front-loaded
  batch, not a new approval checkpoint.

## Notes

- Related but distinct, do not merge: `228-brainstorm-recheck-claude-md-before-designing.md` and
  `242-brainstorm-widen-ask-gate-to-claude-md-parity.md` are both about CLAUDE.md parity in the
  ask gate. This one is about missing external context on greenfield work.
- Also observed that session and already covered by `261-skills-lack-auq-timeout-handling.md`: an
  `ask_user_question` card sat unanswered and blew a 1800s MCP idle timeout, which surfaced as a
  tool error mid-brainstorm. No new todo needed.
- completed, commit 540c946
