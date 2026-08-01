---
name: close
description: Session retrospective, code-health review, persist, close terminal.
disable-model-invocation: true
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
- Empty remaining args = bare /close (retrospect + persist, then close unless --dont-close).

Examples:

- `/close /commit pushnbump` → dont-close: false, chain: `[/commit pushnbump]`
- `/close --dont-close /commit v` → dont-close: true, chain: `[/commit v]`
- `/close /sleep-when-done` → dont-close: false, chain: `[/sleep-when-done]`

## Role

Honest reviewer, not cheerleader. Same anti-sycophancy bar as /rate-it. If session was sloppy, say so. No silver linings, no "great work today".

## When to run

Manual only. The dev triggers /close when a session reaches a natural end. Never auto-fire on token thresholds: deciding "this session is done" is what makes the retrospective land.

## Host app integration (Claude Conductor)

When this session is hosted by Claude Conductor (claude_usage_in_taskbar), the host handles the "Closing" row state and the teardown itself - no text markers:

- **Closing state:** the host marks the row "Closing" automatically the moment a `/close` turn starts (it sees the prompt began with `/close`). Nothing to emit for this.
- **Teardown:** confirmed by calling the `close_session` MCP tool in Phase 6 (see below), NOT by any text output. The host then ends the session and kills the process at turn completion.

If the `close_session` tool isn't available (a plain terminal session not hosted by Conductor), just skip it - the Phase 6 script still closes the terminal as usual. Never emit `<cc-close:*>` text markers; they're retired.

## Phase 0 - Safe-to-close check

Runs first, before Phase 1, every time - no flag skips it.

Resolve this session's screenshot-subfolder id now: `<ancestor-pid>-<ancestor-start-ticks>`, from the same process-tree walk as `rename-session.ps1`/`.sh` (the nearest `claude`-named ancestor process). The start-time suffix is load-bearing, not decoration: Windows recycles PIDs, so a bare PID can collide with a dead session that left files behind; PID plus start time cannot. PowerShell: `$p = Get-Process -Id $ancestorPid; $id = "$($p.Id)-$($p.StartTime.Ticks)"`. Also note whether this session captured any screenshots at all. Phase 3 step 3 uses both: the id scopes the purge to this session's own subfolder, and the zero-writes flag skips the purge entirely when the answer is none.

Scan the full session for dev-stated commitments: explicit multi-part asks ("we need to do X, Y, Z"), a numbered plan the dev agreed to, or any request with more than one part. For each, check whether it actually got done by the time `/close` was invoked.

This is distinct from Phase 1 step 5 (Claude's own unexecuted "want me to...?" offers) - this catches things the dev asked for, not things Claude proposed unprompted.

If everything the dev asked for was completed: proceed silently to Phase 1, no output from this phase.

If anything is unfinished AND this `/close` was triggered interactively (the dev typed it, or it's a live chain the dev is watching): print a short list (what was asked, what state it's in), then ask via `AskUserQuestion` with exactly two options:

- **Finish it first** - pause `/close`, do the unfinished work, then resume at Phase 1.
- **Close anyway** - proceed through the rest of `/close` with the item left unfinished. Hand it to Phase 3 to be filed as a `task` todo (same treatment as an unfinished offer) so it isn't lost.

If anything is unfinished AND `/close` was chained non-interactively (`/sleep-when-done`, autopilot, or any unattended run with nobody to answer a prompt): never block on `AskUserQuestion` - auto-file each unfinished item straight to Phase 3 as a `task` todo (same treatment as "close anyway") and continue.

No silent-drop path either way - every unfinished item either gets done now, or gets filed.

## Phase 1 - Retrospective

Scan the full session. Compute all bullets below internally every time - Phase 3 persists from them regardless of whether anything gets printed.

### Transcript grounding (long sessions only)

"The full session" means the raw transcript on disk, not just what's still in context. Claude Code auto-compacts as it approaches the context limit, so on a long session the early material is already summarized away by the time /close runs - exactly the window where corrections and hard-won facts live. Recalling from a compacted view systematically under-reports them.

Resolve this session's transcript:

1. Read `~/.claude/sessions/*.json` (one per session: `pid`, `sessionId`, `cwd`, `startedAt`). Pick the entry whose `cwd` matches this session's cwd with the newest `startedAt`. That gives `sessionId`.
2. The transcript is `~/.claude/projects/<sanitized-cwd>/<sessionId>.jsonl`, where the folder name is the absolute cwd with `\`, `/`, `:` and spaces replaced by `-` (e.g. `C:\Users\tecno\Desktop\Projects\fibo` -> `C--Users-tecno-Desktop-Projects-fibo`).
3. Fallback if step 1 finds no match: in that project folder, take the most recently modified top-level `*.jsonl`. Ignore `<sessionId>/subagents/agent-*.jsonl` - that's commissioned subagent work, not the dev's own turns.

**Skip this entirely if the transcript is under ~500 lines** - the session was short, nothing compacted, in-context history is already complete and re-reading is wasted tokens.

When it does run: `Grep` the file, never `Read` it whole (transcripts embed full tool payloads and run to megabytes). Target the dev's own turns - lines with `"type":"user"` whose content is text rather than a `tool_result` - since bullets 2 and 5 below are about what Joe said. Pull only enough surrounding context to judge each hit.

### What to compute

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

1. **Memory writes.** Read `~/.claude/refs/memory-rubric.md` first if it hasn't been read this session - it defines the ADD/UPDATE/DELETE/NONE gate, the bar for writing at all, and the evidence requirement. Then for each correction or non-obvious confirmation from Phase 1, route it through that gate and write to the store CLAUDE.md's Global Knowledge Vault section says it belongs in (vault for cross-project facts and people, native per-project Auto Memory for project-local ones), updating the relevant index. Skip if nothing qualifies; NONE is a normal outcome. Never invent memories to look productive.

   **Dedup against this session's own writes.** Memories written live earlier in this session are already covered - list them before evaluating, and treat a Phase 1 candidate matching one as NONE rather than writing a near-duplicate. The transcript sweep exists to catch what live capture MISSED, not to re-extract what it already got.
2. **`.claude/todos/`** Write a separate `.md` file per item from:
   - Phase 0 (unfinished dev commitments where the dev chose "close anyway") - tag `**Type:** task`.
   - Phase 1 step 5 (unfinished offers) - tag `**Type:** task`.
   - Phase 1 steps 3-4 (repeated manual steps, skill rule violations) - tag `**Type:** skill-improvement`, Approach section names the skill file involved.

   Follow `ai-todos-format.md` (this skill's folder) for everything: template, filename/id rules, git-policy self-heal. The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items. Note: Phase 2 review findings are written to the backlog by `/code-check` directly - do not re-write them here.
3. **Screenshot cleanup.** Ownership is proven by subfolder, never inferred from mtime - a concurrent session's files can be newer OR older than this session's start and mtime cannot tell them apart. This session may delete ONLY files under its own `.for_bepy/screenshots/<pid>-<start-ticks>/` subfolder (the Phase 0 id) - never files at the folder root, never another session's subfolder, regardless of age. If Phase 0 recorded zero screenshots captured this session, skip deletion entirely, even if a subfolder happens to exist. Before deleting anything, print the exact filenames about to be removed, then delete - never pipe straight to `Remove-Item` without capturing names first. Loose files at the `.for_bepy/screenshots/` root are legacy (written by skills that don't yet use the per-session subfolder) - never auto-delete them, just report the count. Scope is strictly `.for_bepy/screenshots/` - never touch `.portfolio-data/` (portfolio keepers), committed assets, or any image elsewhere. Delete without a blocking prompt (still runs unattended under `/sleep-when-done`/autopilot). Skip silently if the folder or this session's subfolder is missing or empty. PowerShell: `$files = Get-ChildItem -File ".for_bepy/screenshots/$id" -ErrorAction SilentlyContinue; $files | ForEach-Object { $_.Name }` to list and print, then `$files | Remove-Item -Force` (`$id` is Phase 0's pid-plus-start-ticks, never a bare pid).
Note: there is no implicit /commit step anymore. If the dev wants a commit, they chain `/commit` (with whatever subcommand they want) into the /close call.

## Phase 4 - Counter summary

Print one line, always - this is the one thing Joe reliably sees from Phases 1-3:

```
N memory writes . N todos written (M from review, K skill-improvement) . N screenshots cleaned (M legacy at root, untouched) . chain: <list of chained commands or "none"> . closing: yes/no
```

`M from review` is the count of findings from Phase 2 (size + DRY + dead code). If Phase 2 was skipped, omit the parenthetical and say `review skipped`. `K skill-improvement` is the subset of this close's todos tagged `skill-improvement` in Phase 3 step 2; omit `, K skill-improvement` if zero. `N screenshots cleaned` is the count deleted from this session's own subfolder in Phase 3 step 3 (0 if this session took no screenshots, its subfolder was missing/empty, or nothing qualified). `M legacy at root, untouched` is the count of loose root-level files left alone because they predate the per-session subfolder scheme; omit the parenthetical if that count is 0.

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

If all clear: first, if the `close_session` MCP tool is available (Conductor-hosted session), call it once - this is the host's authoritative teardown confirmation, so the session ends and its process is killed at turn completion. Never call it if any skip condition above applies; skip it silently in a plain terminal session where the tool doesn't exist.

**HARD ORDERING RULE:** running the rename/kill script WITHOUT having called `close_session` first, in a session where that tool exists, leaves Conductor chats permanently un-closed - killing the process is MEANINGLESS to the daemon, it respawns the process every turn, so only the tool call actually ends the chat. If `close_session` is in your tool list, the script line below is FORBIDDEN until the tool call has returned.

Then run for your OS (literal paths hardcoded - dynamic `$env:` expressions fail the harness permission matcher and cause per-invocation prompts):

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
- Trying to invoke `/exit` as a skill or chained command. Terminal kill is now built into Phase 6 by default.
