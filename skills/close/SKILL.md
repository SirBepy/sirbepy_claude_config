---
name: close
description: Triggers on /close only. Session retrospective, code-health review, persist, rename, close terminal.
argument-hint: "[--dont-close] [--skip-review] [--light] [/commit ...] [/sleep-when-done]"
---

# /close

> Retrospect, review, persist, rename, close terminal.

## Usage

```
/close                                  # retrospect + review + persist + rename + close terminal
/close --dont-close                     # everything except closing, then prompts to run /clear
/close --skip-review                    # skip the parallel code-health review subagents
/close --light                          # high-context mode: short Phase 1, delegate Phase 2+3 to subagents
/close /commit                          # commit, then close terminal
/close /commit pushnbump                # commit pushnbump, then close terminal
/close --dont-close /commit             # commit but keep terminal open
/close /commit /sleep-when-done        # commit, sleep PC, then close terminal
```

### Arg parsing

`--dont-close`, `--skip-review`, and `--light` are boolean flags, not chained commands. Strip them out first, then parse the rest.

If `--light` is passed: read `close/light.md` before proceeding. It overrides Phases 1-3 with high-context-mode versions.

Remaining args are a chain of slash commands. Each slash command may be followed by its own positional args (anything until the next `/`).

- A token starting with `/` opens a new chained command.
- Tokens between `/foo` and the next `/bar` are `/foo`'s args.
- Empty remaining args = bare /close (retrospect + persist + rename, then close unless --dont-close).

Examples:

- `/close /commit pushnbump` → dont-close: false, chain: `[/commit pushnbump]`
- `/close --dont-close /commit v` → dont-close: true, chain: `[/commit v]`
- `/close /sleep-when-done` → dont-close: false, chain: `[/sleep-when-done]`

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
5. **Unfinished offers.** Scan the session for any "want me to...?" / "should I...?" / "next we could..." offer Claude made that did not get executed. Each one is a candidate for AI_TODOS (will be persisted in Phase 3). List them as: `[file/target] - [action] - [reason]`. If none, say "none".
6. **Verdict.** One sentence: was the session efficient, mid, or wasted effort? Pick one. No hedging.

## Phase 2 - Code Health Review

Skip this entire phase if EITHER:

- `--skip-review` was passed.
- Zero code files changed this session (only docs/config/`.for_bepy/`/memory edits).

Use `git diff --name-only` against the session's starting HEAD (or unpushed commits if commits were made) to get the changed code-file list. Treat `.md`, `.json`, `.toml`, `.yaml`, `.yml`, `.gitignore`, files under `.for_bepy/`, and files under `memory/` as non-code for this gate.

### Step 2a - Inline size check

Cheap, no subagent. For each changed code file: line count it. If > 400 lines AND has an obvious split seam (separate concerns, reusable unit, clear boundary), record a finding: `{ "title": "...", "files": [...], "problem": "[file] is N lines, mixes [X] and [Y]", "fix": "split at [boundary] into [new file]" }`. If no obvious seam, skip that file.

### Step 2b - Parallel review subagents

Dispatch TWO `Agent` calls **in a single message** (parallel) using `subagent_type: "Explore"` (read-only is sufficient). Each agent gets fresh context - the bloated session context is the whole reason we're delegating.

**Agent 1 - DRY check.** Prompt template:

> Review the following changed files for duplication against the existing codebase. Files: `<list>`. For each new component/hook/function/module/util introduced, grep the rest of the repo for equivalents (similar name, similar shape, similar purpose). For each duplicate found, return one finding with: `title` (short), `files` (array of `path:line` for both new and existing), `problem` (one sentence: what duplicates what), `fix` (one-line action: e.g. "delete X and import Y" / "extract shared util to Z"). Return ONLY a JSON array of findings - no prose, no preamble. Empty array if none. Under 300 words total.

**Agent 2 - Dead code.** Prompt template:

> Review the following changed files for dead code: `<list>`. Look for: unused exports, unreachable branches, commented-out blocks left in, variables/imports never read, functions never called. For each finding return: `title` (short), `files` ([path:line]), `problem` (one sentence), `fix` (one-line action: "delete", "uncomment if needed", "wire up at X"). Return ONLY a JSON array of findings - no prose. Empty array if none. Under 300 words total.

### Step 2c - Collect findings

Parse both agents' JSON arrays. Merge with the inline size findings into one list. This list is consumed in Phase 3 step 4 (ai_todos write).

If any agent returns malformed JSON or errors, log the failure and continue with whatever findings parsed cleanly. Don't abort.

## Phase 3 - Persist

Run in this order:

1. **Memory writes.** Per the auto-memory protocol in CLAUDE.md. For each correction or non-obvious confirmation from Phase 1, write or update the appropriate memory file and update MEMORY.md index. Skip if nothing qualifies. Never invent memories to look productive.
2. **`.for_bepy/COMMENTS.md`** Per CLAUDE.md rules.
3. **`.for_bepy/BEPY_TODOS.md`** Reconcile: delete completed steps. Per CLAUDE.md rules.
4. **`.for_bepy/ai_todos/`** For each item from Phase 1 step 5 (unfinished offers) and each finding from Phase 2 (size + DRY + dead code), write a separate `.md` file using the template defined in CLAUDE.md (`# title`, `## Goal`, `## Context`, `## Approach`, `## Acceptance`). Filename: zero-padded numeric prefix + kebab-case slug per the CLAUDE.md ai_todos rules (scan existing files for max id, add 1, never reuse). For Phase 2 findings, use the structured fields directly: `title` → filename slug + `# title` heading; `problem` → `## Context`; `fix` → `## Approach`; `files` → cited inside Context. The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items.
5. **Morning prompt.** If the session had meaningful work (commits made, non-trivial decisions taken), invoke `/next-ai-prompt --caller "/close" --mode close`. Skip if the session was trivial (config tweaks, doc edits, read-only exploration).

Note: there is no implicit /commit step anymore. If the dev wants a commit, they chain `/commit` (with whatever subcommand they want) into the /close call.

## Phase 4 - Rename session

> **Why-literal:** The rename-session.ps1 path is hardcoded to `C:\Users\tecno\...` on purpose. The harness's permission matcher refuses to validate dynamic command names (`$env:` vars, expressions, globs) and falls back to always-prompt for every invocation. A literal path keeps /close at one prompt instead of N. Do NOT "portable-ize" this - it will re-introduce permission spam. This is a documented constraint, not a leaked username.

Give the session a meaningful name so the `/resume` picker is browsable later.

1. Pick a short human-readable name (max 60 chars), sentence-style with spaces, written like a commit subject. Sentence case, no kebab-case, no trailing period. Use Phase 1 retrospective as input.
   - Good: `Improve /close skill with auto-rename`, `Fix killbrick poison type damage`, `Investigate session rename storage`
   - Bad: `close-skill-rename-test`, `session-2025-05-02`, `chat-1`, `Updated some files.`
2. Run the helper:
   ```powershell
   & "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Name "<name>"
   ```
   The script finds the current session jsonl by matching cwd, then appends the two records the harness uses for renames (`custom-title`, `agent-name`). Idempotent enough - last record wins per harness logic.
3. If the script errors (no matching session, jsonl not found), print the error and continue. Don't abort the close.

The rename takes effect on next launch / `/resume` picker. It does NOT update the current session's prompt bar live.

## Phase 5 - Counter summary

Print one line:

```
N memory writes . N comments . N workflow reconciles . N ai_todos written (M from review) . renamed to "<name>" . chain: <list of chained commands or "none"> . closing: yes/no
```

`M from review` is the count of findings from Phase 2 (size + DRY + dead code). If Phase 2 was skipped, omit the parenthetical and say `review skipped`.

## Phase 6 - Run chained commands

Walk the parsed chain in user order. Invoke each via the `Skill` tool with its args. Wait for each to return before moving to the next.

If any chained command fails (errors, hook rejection, etc.):

- Stop the chain right there. Do not run subsequent commands.
- Skip Phase 7 (terminal kill) - failure means there may be unsaved state worth keeping the window open for.
- Print which command failed and why.

If no chained commands, skip this phase.

## Phase 7 - Close terminal

**Default: always run.** Skip only if ANY of these are true:

- `--dont-close` was passed.
- Any chained command in Phase 6 failed.
- The rename script in Phase 4 errored.
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.

If all clear, run (literal path - see Phase 4 Why-literal callout):

```powershell
& "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Name "<name>" -Close
```

The script walks up to the parent shell process (powershell.exe hosting the terminal tab) and kills it, closing the terminal. The detached killer waits 800ms so this final response flushes first.

If kill was skipped, print on its own line:

- If `--dont-close`: `Terminal kept open. Run /clear or close manually.`
- If other reason: `Exit skipped: <reason>. Run /clear or close manually.`

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Auto-committing without `/commit` in the chain. Dev opts in explicitly now.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
- Trying to invoke `/exit` as a skill or chained command. Terminal kill is now built into Phase 7 by default.
