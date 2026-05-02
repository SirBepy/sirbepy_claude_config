---
name: close
description: Triggers on /close and its subcommands (any /commit subcommand: v, bump, onlybump, onlyv, push, pushbump, pushnbump). Session retrospective: brutal review, health checks, persist to .for_bepy/ and memory, commit, rename session, kill claude.exe.
---

# /close

> Session-end retrospective. Persist learnings, hand off to /commit, rename session, kill the process.

## Usage

```
/close                          # plain commit + kill
/close push                     # forwards "push" to /commit, then kills
/close pushnbump                # forwards "pushnbump" to /commit, then kills
/close dontkill                 # plain commit, NO kill
/close pushnbump dontkill       # commit subcommand + skip the kill
/close <commit-subcommand> [dontkill]
```

Args after `/close` are space-separated tokens. Parse them as:
- The `dontkill` token (anywhere in args) sets a flag that skips the Phase 3 kill. Do NOT forward `dontkill` to /commit.
- Any other token is treated as the /commit subcommand and forwarded verbatim. Valid /commit subcommands: `v`, `bump`, `onlybump`, `onlyv`, `push`, `pushbump`, `pushnbump`. If the token doesn't match any of these, still forward it - /commit handles validation.
- If no commit-subcommand token is present, call /commit with no arg.

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
5. **Commit.** Hand off to /commit skill, forwarding whatever subcommand arg the dev passed to /close. Do not bypass /commit.

## Phase 2.5 - Rename session

After /commit returns, give the session a meaningful name so the `/resume` picker is browsable later.

1. Pick a short human-readable name (max 60 chars), sentence-style with spaces, written like a commit subject. Sentence case, no kebab-case, no trailing period. Use Phase 1 retrospective as input.
   - Good: `Improve /close skill with auto-rename`, `Fix killbrick poison type damage`, `Investigate session rename storage`
   - Bad: `close-skill-rename-test`, `session-2025-05-02`, `chat-1`, `Updated some files.`
2. Run the helper:
   ```powershell
   & "$env:USERPROFILE\.claude\skills\close\rename-session.ps1" -Name "<name>"
   ```
   The script finds the current session jsonl by matching cwd, then appends the two records the harness uses for renames (`custom-title`, `agent-name`). Idempotent enough - last record wins per harness logic.
3. If the script errors (no matching session, jsonl not found), print the error and continue. Don't abort the close.

The rename takes effect on next launch / `/resume` picker. It does NOT update the current session's prompt bar live.

## Phase 3 - Close

1. Print one-line counter summary:
   ```
   N memory writes . N comments . N workflow reconciles . N skill candidates . N commits . renamed to "<name>"
   ```
2. **Safety check before kill.** Skip the kill (jump to step 4) if ANY of these are true:
   - The dev passed the `dontkill` token in the /close args.
   - /commit failed or was skipped.
   - The rename script in Phase 2.5 errored.
   - Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.
   - The dev explicitly said "don't close" or "stay open" anywhere in this session.
3. **Kill claude.exe.** If safety check passed, run:
   ```powershell
   & "$env:USERPROFILE\.claude\skills\close\rename-session.ps1" -Name "<name>" -Close
   ```
   (Same script, with `-Close`. It re-resolves the session pid, spawns a detached PowerShell that waits 800ms then terminates the claude process. The wait gives this final response time to flush to the terminal.)
   - If you already ran the rename earlier in Phase 2.5, that's fine: re-running with same name + `-Close` just re-appends the rename records (last write wins) and schedules the kill. No duplication harm.
4. If kill was skipped, print on its own line: `Run /clear now.` (so the dev still has a way to reset context manually).
5. Done. No closing fluff.

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Skipping /commit and committing directly. Always hand off.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
