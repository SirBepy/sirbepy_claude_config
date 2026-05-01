---
name: close
description: Triggers on /close only. Session retrospective: brutal review, health checks, persist to .for_bepy/ and memory, commit.
---

# /close

> Session-end retrospective. Persist learnings, hand off to /commit.

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
5. **Unfinished offers.** Scan the session for any "want me to...?" / "should I...?" / "next we could..." offer Claude made that did not get executed. Each one is a candidate for AI_TODOS (will be persisted in Phase 2). List them as: `[file/target] - [action] - [reason]`. If none, say "none".
6. **Verdict.** One sentence: was the session efficient, mid, or wasted effort? Pick one. No hedging.

## Phase 1.5 - Code Health Checks

Run these after the retrospective, before persisting. Only flag real issues - not every file touched.

### Large files (400+ lines)
For each file edited or created this session: if it exceeds 400 lines AND has an obvious split seam (separate concerns, reusable unit, clear boundary), note it. One line: `[file] is N lines - consider splitting at [boundary]`. If no obvious seam, skip it.

### Duplicate detection
Check unpushed commits (`git log @{u}..HEAD` or `git log origin/HEAD..HEAD`). For any new component, hook, function, or module introduced: do a quick grep to see if something equivalent already existed. If a duplicate is found: `[new thing] duplicates [existing thing] at [path]`. One line per finding.

Skip both checks entirely if no files were edited this session.

## Phase 2 - Persist

Run in this order:

1. **Memory writes.** Per the auto-memory protocol in CLAUDE.md. For each correction or non-obvious confirmation from Phase 1, write or update the appropriate memory file and update MEMORY.md index. Skip if nothing qualifies. Never invent memories to look productive.
2. **`.for_bepy/COMMENTS.md`** Per CLAUDE.md rules.
3. **`.for_bepy/BEPY_TODOS.md`** Reconcile: delete completed steps. Per CLAUDE.md rules.
4. **`.for_bepy/ai_todos/`** For each item from Phase 1 step 5 (unfinished offers) and Phase 1.5 (large files / duplicates), write a separate `.md` file using the template defined in CLAUDE.md (`# title`, `## Goal`, `## Context`, `## Approach`, `## Acceptance`). Filename: zero-padded numeric prefix + kebab-case slug per the CLAUDE.md ai_todos rules (scan existing files for max id, add 1, never reuse). The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items.
5. **Commit.** Hand off to /commit skill. Do not bypass it.

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
