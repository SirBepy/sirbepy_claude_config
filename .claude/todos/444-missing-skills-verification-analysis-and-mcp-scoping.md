<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=4, reconfirm-count=3, content-hash=bfd86f7a -->
<!-- duplicate-checked -->
# Three smaller skill gaps: real-system verification, analytical Q&A, per-launch MCP scoping

**Type:** task
**Origin:** ai

## Goal

Assess and, where they earn it, adopt the three remaining skill-shaped gaps from the harvest. Each is
small enough that a separate todo would be overhead, and each needs a genuine adopt-or-skip call rather
than automatic adoption.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

**1. `prove-it-works`** (`repos/ooloth_dotfiles/tools/agents/config/skills/prove-it-works/SKILL.md`)

A 5-step QA skill: Survey, Run, Gap-audit, Decide, Report. It forces running the **real system** end to
end rather than the tests, tabulates path plus observed plus evidence, and asks the load-bearing
question: "how would I observe this if I had no test suite at all?"

Why it fits: CLAUDE.md's testing floor is a list of commands to run (typecheck, unit, lint, build) and
says nothing about observing the actual system. This repo already learned that lesson the hard way, and
it is recorded in `refs/delegation-doctrine.md`: a builder returned 11/11 typecheck, 105 tests and 4/4
builds green while shipping a screen nothing like the approved mockup, because a stale Vite dependency
shadow was invisible to every automated check. The doctrine's response was a rule that visual work must
produce a rendered artifact. `prove-it-works` generalizes that beyond visual work.

Overlap to resolve: the doctrine's visual-work rule and the UI screenshot reminder hook already cover
the visual case. This would cover the non-visual case (a CLI, a hook, a data flow).

**2. Analytical Q&A with a quality gate** (`repos/solatis_claude-config/.../deepthink`, 14-step Full
mode)

Real sub-agent dispatch with a Quality Gate marking each sub-agent PASS/PARTIAL/FAIL, plus a bounded
5-iteration independent-verification loop before final formatting.

Why it might fit: `/iterate-it` converges an implementation and `/rate-it` scores a change. Neither
answers an open-ended analytical question with structured verification. Sessions like this harvest do
that ad hoc.

Why it might not: this may be exactly what `/brainstorm` plus `/delegate` already produce when used
together, and adding a skill for a workflow already achievable by composition is pure
description-budget cost. The honest test is whether a recent real question would have gone better under
it.

**3. Per-launch MCP scoping** (`repos/TheoBrigitte_claude-config/claudy/main.go`)

A CLI wrapper choosing which MCP servers load per invocation (`--mcp-servers github,slack`,
`--preset sre`) via `--strict-mcp-config`, instead of one static always-on list.

Why it fits: this session's own reminder lists ten claude.ai connectors requiring auth (Asana,
Atlassian, Box, Canva, Figma, HubSpot, Intercom, Linear, Notion, monday.com) plus mobbin and the
Conductor server. Most are irrelevant to any given session, and each one's tool schemas are context and
attack surface. Note the harness already defers most tool schemas via `ToolSearch`, which mitigates the
context half considerably, so the remaining argument is mostly about surface and startup, not tokens.

Why it might not: it needs a launcher wrapper, and memory records that the PowerShell profile already
carries several `claude` wrappers, so this would extend an existing pattern rather than create one.
Check whether `--strict-mcp-config` even exists in this harness version before designing anything.

## Approach

1. Take these one at a time and give each an explicit adopt-or-skip verdict with a reason. **Skipping
   two of three is a perfectly good outcome**; the 2026-08-01 audit deleted 12 skills, so adding
   marginal ones has a real cost.
2. For `prove-it-works`: read it, then check it against the doctrine's visual-work rule and the UI
   screenshot hook. If it only duplicates them, skip it. If it genuinely covers the non-visual case,
   adopt it scoped to that, and cross-reference the doctrine rather than restating it.
3. For analytical Q&A: before building anything, take one real analytical question from recent history
   and ask whether `/brainstorm` plus `/delegate` handled it adequately. If yes, skip. If no, name the
   specific thing that was missing, and only then design.
4. For MCP scoping: first verify `--strict-mcp-config` exists in this version. Then check the existing
   PowerShell profile wrappers. If it is a small addition to a wrapper that already exists, it is worth
   it; if it needs a new launcher, weigh that against a benefit that `ToolSearch` already partly
   provides.
5. For anything adopted, check the model-invocable description budget against todo 400, which is live
   and already about two descriptions being over budget.

## Acceptance

- Three explicit verdicts with reasons. Skips are recorded, not silently dropped.
- `prove-it-works`, if adopted, is scoped to the non-visual case and cross-references the doctrine's
  visual rule instead of duplicating it.
- The analytical Q&A decision cites one real question and what actually happened, not a hypothetical.
- The MCP flag is verified to exist before any wrapper work.
- Anything adopted has been used once on real work, and that is reported.

## Notes

The default answer for all three should be skip unless a concrete case argues otherwise. Three
plausible-sounding skills is exactly the kind of addition that produced a 12-skill deletion audit.

Do not adopt all three to be thorough. Thoroughness here is the reasoning, not the count.

**SETTLED 2026-08-20 by Joe, do not re-litigate: `prove-it-works` is SKIPPED.** On reading the
harvest report his response was "sounds like my test and e2e skills, no?" and that is correct - it
overlaps `/test` and `/e2e`, which were deliberately split on 2026-08-19 precisely so fast checks and
browser-driven runs had separate homes. Adopting a third skill over the same ground would cost
description budget for nothing.

The one non-redundant element is its framing question, "how would I observe this if I had no test
suite at all?" That is worth **one line added to `/e2e`**, not a skill. Do that instead, and treat
item 1 of this todo as closed.

Items 2 (analytical Q&A) and 3 (MCP scoping) are untouched by this and still need their own verdicts.

**Correction, 2026-09-01 (`/cleanup-todos` deep pass).** The paragraph above treats item 1 as
closed, but it was never actually done: `skills/e2e/SKILL.md` contains no such line, verified by
reading the file. Item 1 is still open along with items 2 and 3.
