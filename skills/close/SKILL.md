---
name: close
description: Triggers on /close only. Session retrospective + persist + rename. Optional chained slash commands run after (e.g. /close /commit pushnbump /exit).
argument-hint: "[/commit ...] [/sleep-when-done] [/exit]"
---

# /close

> Session retrospective, persist, rename. Optionally chain follow-up slash commands.

## Usage

```
/close                                  # retrospect + persist + rename only
/close /commit                          # ... then commit
/close /commit pushnbump                # ... then commit pushnbump
/close /exit                            # ... then kill window
/close /commit pushnbump /exit          # commit, then kill window
/close /commit pushnbump /sleep-when-done   # commit, then sleep PC
```

### Arg parsing

Args after `/close` are a chain of slash commands. Each slash command may be followed by its own positional args (anything until the next `/`).

- A token starting with `/` opens a new chained command.
- Tokens between `/foo` and the next `/bar` are `/foo`'s args.
- Empty arg list = bare /close (retrospect + persist + rename, nothing more).

Examples:
- `/close /commit pushnbump /exit` → chain: `[/commit pushnbump]`, `[/exit]`
- `/close /sleep-when-done` → chain: `[/sleep-when-done]`
- `/close /commit v` → chain: `[/commit v]`

### Smart ordering

`/exit` always runs last regardless of where it appears in the chain. Everything else preserves user order. Rationale: the dev sometimes writes `/close /exit /commit` thinking "and also commit", but commit must happen before the window dies.

Other terminal-ish commands (`/sleep-when-done`) stay in user order - they're not the same as `/exit`. Dev controls placement.

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

Note: there is no implicit /commit step anymore. If the dev wants a commit, they chain `/commit` (with whatever subcommand they want) into the /close call.

## Phase 2.5 - Rename session

Give the session a meaningful name so the `/resume` picker is browsable later.

1. Pick a short human-readable name (max 60 chars), sentence-style with spaces, written like a commit subject. Sentence case, no kebab-case, no trailing period. Use Phase 1 retrospective as input.
   - Good: `Improve /close skill with auto-rename`, `Fix killbrick poison type damage`, `Investigate session rename storage`
   - Bad: `close-skill-rename-test`, `session-2025-05-02`, `chat-1`, `Updated some files.`
2. Run the helper. The path MUST be a string literal (no `$env:` vars, no expressions) - the harness's permission matcher refuses to validate dynamic command names and falls back to always-prompt:
   ```powershell
   & "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Name "<name>"
   ```
   The script finds the current session jsonl by matching cwd, then appends the two records the harness uses for renames (`custom-title`, `agent-name`). Idempotent enough - last record wins per harness logic.
3. If the script errors (no matching session, jsonl not found), print the error and continue. Don't abort the close.

The rename takes effect on next launch / `/resume` picker. It does NOT update the current session's prompt bar live.

## Phase 3 - Counter summary

Print one line:
```
N memory writes . N comments . N workflow reconciles . N skill candidates . renamed to "<name>" . chain: <list of chained commands or "none">
```

## Phase 4 - Run chained commands

Walk the parsed chain in smart-ordered sequence (`/exit` deferred to last; everything else in user order).

For each chained command:
- If it's `/exit`: handled in Phase 5 (don't invoke it as a skill - `/exit` is a CLI built-in, but inside this skill we substitute it with our kill mechanism).
- Otherwise: invoke it via the `Skill` tool with its args. Wait for it to return before moving to the next.

If any chained command fails (errors, hook rejection, etc.):
- Stop the chain right there. Do not run subsequent commands.
- If `/exit` was queued, **skip it** - failure means there may be unsaved state worth keeping the window open for.
- Print which command failed and why.

If no chained commands, skip this phase.

## Phase 5 - Exit (only if /exit was in the chain)

Skip the kill if ANY of these are true:
- `/exit` was not in the chain.
- Any earlier chained command failed.
- The rename script in Phase 2.5 errored.
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.
- The dev explicitly said "don't close" or "stay open" anywhere in this session.

If all clear, run (literal path, no `$env:` vars - see Phase 2.5 note):
```powershell
& "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Name "<name>" -Close
```
The script re-resolves the session pid, spawns a detached PowerShell that waits 800ms then terminates the claude process. The wait lets this final response flush.

If kill was skipped (and `/exit` was in the chain), print on its own line: `Exit skipped: <reason>. Run /clear or /exit manually.`

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Auto-committing without `/commit` in the chain. Dev opts in explicitly now.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
- Trying to invoke `/exit` as a skill. It's a CLI built-in; substitute the rename-session.ps1 -Close call.
