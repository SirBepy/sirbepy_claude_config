---
name: close
description: Triggers on /close only. Session retrospective, code-health review, persist, close terminal.
argument-hint: "[--dont-close] [--skip-review] [--light] [/commit ...] [/sleep-when-done]"
---

# /close

> Retrospect, review, persist, close terminal.

## Usage

```
/close                                  # retrospect + review + persist + close terminal
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

## Lifecycle markers (host app integration)

The first line of output, before anything else (before Phase 1, as plain text - not in a code block): emit `<cc-close:starting>`. This is how a hosting app (e.g. claude_usage_in_taskbar) knows the skill is genuinely running and marks the session "closing" - it must never appear anywhere except as the very first line, and never appear at all in a plain terminal session that isn't hosted by such an app's parser (harmless either way: it's a no-op line of text there). Skip this marker entirely if you are not actually going to execute this skill (e.g. arg parsing fails before any phase starts).

The closing counterpart `<cc-close:done>` is emitted in Phase 6 below - it confirms the terminal is genuinely about to be killed, and must be skipped whenever Phase 6 itself is skipped.

## Phase 1 - Retrospective

Scan the full session. Compute all bullets below internally every time - Phase 3 persists from them regardless of whether anything gets printed.

1. **Detours.** Tool calls, file reads, or directions taken that turned out unneeded. Each = signal of missing context up front or wrong skill firing.
2. **Corrections.** Places the dev pushed back, rejected, or rewrote your output. What rule was missing or violated?
3. **Repeated manual steps.** Anything done 2+ times manually that should be a skill. List name + one-line scope. Candidate for a `skill-improvement` ai_todo (persisted in Phase 3). Do NOT draft the skill inline.
4. **Skill rule violations.** Active skills whose rules got broken. Pointer to skill + which rule. Candidate for a `skill-improvement` ai_todo (persisted in Phase 3). Enforcement gap, not a "be more careful" fix.
5. **Unfinished offers.** Scan the session for any "want me to...?" / "should I...?" / "next we could..." offer Claude made that did not get executed. Each one is a candidate for a `task` ai_todo (persisted in Phase 3). List them as: `[file/target] - [action] - [reason]`.
6. **Verdict.** One sentence: was the session efficient, mid, or wasted effort? Pick one. No hedging.

### Print rule

Joe does not read this by default - it exists to feed Phase 3. Print the full bullet list ONLY if at least one of 1-4 has a real (non-"none") entry. If everything is empty, print nothing from Phase 1 and let Phase 4's one-line counter be the only visible trace of this phase. Never print "none" bullets just to show the work happened.

## Phase 2 - Code Health Review

Skip this entire phase if ANY:

- `--skip-review` was passed.
- Zero code files changed this session (only docs/config/`.for_bepy/`/`.claude/todos/`/memory edits).
- Fewer than 50 added lines total across all code files (`git diff --shortstat` insertions). Rationale: small diffs are almost always edits to existing code, not new symbol declarations - DRY/dead-code review finds nothing. Saves tokens on routine closes.

Determine scope arg: if commits were made this session, pass `unpushed`; otherwise pass `uncommitted`.

Invoke `/code-check` with that scope arg via the Skill tool. It handles the analysis and writes the todos directly. Read its summary line (`code-check: N findings ...`) to extract the finding count for the Phase 4 counter.

## Phase 3 - Persist

Run in this order:

1. **Memory writes.** Per the auto-memory protocol in CLAUDE.md. For each correction or non-obvious confirmation from Phase 1, write or update the appropriate memory file and update MEMORY.md index. Skip if nothing qualifies. Never invent memories to look productive.
2. **`.claude/todos/`** Write a separate `.md` file per item from:
   - Phase 1 step 5 (unfinished offers) - tag `**Type:** task`.
   - Phase 1 steps 3-4 (repeated manual steps, skill rule violations) - tag `**Type:** skill-improvement`, Approach section names the skill file involved.

   Follow `ai-todos-format.md` (this skill's folder) for everything: template, filename/id rules, git-policy self-heal. The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items. Note: Phase 2 review findings are written to the backlog by `/code-check` directly - do not re-write them here.
3. **Screenshot cleanup.** Delete the contents of `.for_bepy/screenshots/` (the throwaway verification-screenshot quarantine per CLAUDE.md). Scope is strictly that folder - never touch `.portfolio-data/` (portfolio keepers), committed assets, or any image elsewhere. List each file deleted in the output so the dev sees what went. Delete without a blocking prompt (the folder is disposable by definition, and /close runs autonomously when chained with `/sleep-when-done`). Skip silently if the folder is missing or empty. PowerShell: `Get-ChildItem -File '.for_bepy/screenshots/' | Remove-Item -Force`.
Note: there is no implicit /commit step anymore. If the dev wants a commit, they chain `/commit` (with whatever subcommand they want) into the /close call.

## Phase 4 - Counter summary

Print one line, always - this is the one thing Joe reliably sees from Phases 1-3:

```
N memory writes . N todos written (M from review, K skill-improvement) . N screenshots cleaned . chain: <list of chained commands or "none"> . closing: yes/no
```

`M from review` is the count of findings from Phase 2 (size + DRY + dead code). If Phase 2 was skipped, omit the parenthetical and say `review skipped`. `K skill-improvement` is the subset of this close's todos tagged `skill-improvement` in Phase 3 step 2; omit `, K skill-improvement` if zero. `N screenshots cleaned` is the count deleted from `.for_bepy/screenshots/` in Phase 3 step 3 (0 if folder was missing/empty).

## Phase 5 - Run chained commands

Walk the parsed chain in user order. Invoke each via the `Skill` tool with its args. Wait for each to return before moving to the next.

If any chained command fails (errors, hook rejection, etc.):

- Stop the chain right there. Do not run subsequent commands.
- Skip Phase 6 (terminal kill) - failure means there may be unsaved state worth keeping the window open for.
- Print which command failed and why.

If no chained commands, skip this phase.

## Phase 6 - Close terminal

**Default: always run.** Skip only if ANY of these are true:

- `--dont-close` was passed.
- Any chained command in Phase 5 failed.
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.

If all clear: first emit `<cc-close:done>` on its own line as plain text (this is the host app's confirmation that the terminal is genuinely about to die - never emit it if any skip condition above applies). Then run for your OS (literal paths hardcoded - dynamic `$env:` expressions fail the harness permission matcher and cause per-invocation prompts):

**Mac/Linux:**
```sh
sh /Users/josipmuzic/.claude/skills/close/rename-session.sh --close
```

**Windows:**
```powershell
& "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Close
```

The script kills the claude ancestor process after an 800ms delay so this final response flushes first. In VS Code terminals this closes the tab; in Terminal.app it returns to the shell prompt.

If kill was skipped, print on its own line:

- If `--dont-close`: `Terminal kept open. Run /clear or close manually.`
- If other reason: `Exit skipped: <reason>. Run /clear or close manually.`

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Auto-committing without `/commit` in the chain. Dev opts in explicitly now.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
- Trying to invoke `/exit` as a skill or chained command. Terminal kill is now built into Phase 7 by default.
