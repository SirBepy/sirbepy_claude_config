---
name: close
description: Triggers on /close only. Manual session-end retrospective: brutal review of the session, then persist learnings to memory, COMMENTS, WORKFLOWS, and hand off to /commit.
---

# /close

> Session-end retrospective. Persist learnings, commit, suggest rename.

## Role

Honest reviewer, not cheerleader. Same anti-sycophancy bar as /rate-it. If session was sloppy, say so. No silver linings, no "great work today".

## When to run

Manual only. The dev triggers /close when a session reaches a natural end. Never auto-fire on token thresholds: deciding "this session is done" is what makes the retrospective land.

## Phase 1 - Retrospective

Scan the full session. For each bullet below, output specific examples or "none". No vague filler.

1. **Detours.** Tool calls, file reads, or directions taken that turned out unneeded. Each = signal of missing context up front or wrong skill firing.
2. **Corrections.** Places the dev pushed back, rejected, or rewrote your output. What rule was missing or violated?
3. **Repeated manual steps.** Anything done 2+ times manually that should be a skill. List name + one-line scope. Do NOT draft the skill.
4. **Skill rule violations.** Active skills whose rules got broken. Pointer to skill + which rule. Enforcement gap, not a "be more careful" fix.
5. **Verdict.** One sentence: was the session efficient, mid, or wasted effort? Pick one. No hedging.

## Phase 2 - Persist

Run in this order:

1. **Memory writes.** Per the auto-memory protocol in CLAUDE.md. For each correction or non-obvious confirmation from Phase 1, write or update the right file in `~/.claude/projects/C--Users-tecno--claude/memory/` and update MEMORY.md index. Skip if nothing qualifies. Never invent memories to look productive.
2. **COMMENTS_FOR_BEPY.md.** Append anything needing the dev's eyeballs (questions, blockers, decisions to review). Create file if missing. Never reset.
3. **WORKFLOWS_FOR_SIRBEPY.md.** Reconcile: delete completed manual steps. If file empty, delete it.
4. **Commit.** Hand off to /commit skill. Do not bypass it.

## Phase 3 - Close

1. Print one-line counter summary:
   ```
   N memory writes . N comments . N workflow reconciles . N skill candidates . N commits
   ```
2. Done. No closing fluff.

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Skipping /commit and committing directly. Always hand off.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
