---
name: close
description: Retrospect, review, persist, close. Fires on /close as a message's first or last word; finishes open work first.
argument-hint: "[task text] [--now] [--dont-close] [--skip-review] [--light] [/commit ...] [/sleep-when-done]"
---

# /close

> Retrospect, review, persist, close terminal.

Sidecars, read on demand from the phase that names them: `phase0-checks.md`, `grounding.md`, `review-scope.md`, `persist.md`, `finish.md`, `light.md` (`--light`), `ai-todos-format.md` (todo files).

## Usage

```
/close                                  # finish open work, then retrospect + review + persist + close terminal
fix the typo /close                     # do the task first, then the same as /close
/close fix the typo                     # same: task text after the token is also done first
fix the typo /close --now               # do the task, then skip finishing other open work and close
fix the typo /close /sleep-when-done    # do the task, then close, then sleep the PC
/close --now                            # skip finishing and waiting: file unfinished items as todos, then close
/close --dont-close                     # everything except closing, then prompts to run /clear
/close --skip-review                    # skip the parallel code-health review subagents
/close --light                          # high-context mode: short Phase 1, delegate Phase 2+3 to subagents
/close /commit                          # commit, then close terminal
/close /release                         # release (push pipeline plus version bump), then close terminal
/close --dont-close /commit             # commit but keep terminal open
/close /commit /sleep-when-done        # commit, sleep PC, then close terminal
```

### Arg parsing

`--now`, `--dont-close`, `--skip-review`, and `--light` are boolean flags, not chained commands. Strip them out first, then parse the rest. Dev wording that asks to close without finishing ("close now", "close right now", "just close") counts as `--now`.

Task text is any text around the `/close` token that is neither a flag nor a slash command: before it (`fix the typo /close`) or directly after it, up to the first flag or `/command` (`/close fix the typo`). Claude does the task first, then runs /close as usual. `--now` never drops the task: it only skips finishing and waiting on other open work. The three shapes with task text, each with one outcome:

- `/close fix the typo` -> task: fix the typo; flags: none; chain: `[]`. Fix the typo, then bare /close.
- `do X /close --now` -> task: do X; `--now`: true; chain: `[]`. Do X, then close without finishing or waiting on anything else.
- `do X /close /sleep-when-done` -> task: do X; chain: `[/sleep-when-done]`. Do X, then close, then `/sleep-when-done`.

### Trigger

Fires only on a `/close` token the dev typed as the first word of their own message, or as the last word once trailing flags and chained commands are set aside (`do X /close`, `do X /close --now`, `do X /close /sleep-when-done`), or that ends a gate chat's spawn prompt (which carries the dev's push request). Text before a trailing `/close` is a task to finish first (`fix the typo /close`); any other `/command` in it runs as part of that task, per `~/.claude/refs/slash-arg-parsing.md`. Plain text after a leading `/close` is a task too (`/close fix the typo`). Plain text on both sides of a mid-message `/close` (`do X /close then Y`) is not a trigger: the token is neither first nor last. Claude Code only expands a slash command at the very start of a prompt, so a trailing token arrives as plain text and Claude loads this skill through the Skill tool itself; that is why the skill stays model-invocable. Never a trigger: `/close` mid-sentence, inside quotes, code, tool output or skill text, negated or conditional ("don't /close yet", "should I /close?"). If Claude cannot point at the dev's own message starting with the token, or ending with it plus only flags and chained commands, it does not start. Claude also runs it unprompted under CLAUDE.md's "Task done, no question pending: run /close yourself"; that path has nothing in flight by definition, so it never waits.

If `--light` is passed: read `close/light.md` before proceeding. It overrides Phases 1-3 with high-context-mode versions.

Remaining args follow the chaining convention in `~/.claude/refs/slash-arg-parsing.md`: each is a chain of slash commands, and each slash command may be followed by its own positional args (anything until the next `/`). Empty remaining args = bare /close (retrospect + persist, then close unless --dont-close). Examples: `/close /release` -> dont-close: false, chain: `[/release]`; `/close --dont-close /commit v` -> dont-close: true, chain: `[/commit v]`; `/close /sleep-when-done` -> dont-close: false, chain: `[/sleep-when-done]`.

## Role

Honest reviewer, not cheerleader. Same anti-sycophancy bar as /rate-it. If session was sloppy, say so. No silver linings, no "great work today".

## When to run

The dev triggers /close (see Trigger above), or Claude runs it when a task is done with nothing pending. Never auto-fire on token thresholds: deciding "this session is done" is what makes the retrospective land.

Phase 0 starts in the SAME turn /close is invoked, and Phases 1-5 run in that same turn once Phase 0's finishing and waiting are done. Never end a turn to wait for background work to re-invoke the session: on 2026-08-19 a /close that promised to run "once it returns" ended its turn with zero phases, the host marked the chat done, and the retrospective was nearly lost (`.claude/todos/done/close-must-not-be-deferred-behind-background-work.md`). Persistence is the point of this skill, so it cannot hang on optional work forever: Phase 0's wait is in the foreground and capped.

## Host app integration (Claude Conductor)

When this session is hosted by Claude Conductor (claude_usage_in_taskbar), the host handles the "Closing" row state and the teardown itself, with no text markers:

- **Closing state:** the host marks the row "Closing" when Phase 1 calls `close_session` with `stage: "started"`, not when the turn's prompt starts with `/close`. A turn that finishes a task first (Phase 0, a question card in between) therefore shows Closing only once the closing phases begin, and a trailing `/close` (`do X /close`, a gate chat's spawn prompt) shows it too. The host keeps its prompt heuristic only for a prompt that begins `/close --now`.
- **Teardown:** confirmed by calling the `close_session` MCP tool in Phase 6, NOT by any text output. The host then ends the session and kills the process at turn completion.

If the `close_session` tool isn't available (a plain terminal session), skip it; the Phase 6 script still closes the terminal. Never emit `<cc-close:*>` text markers; they're retired.

## Phase 0 - Safe-to-close check

Runs first, before Phase 1, every time - no flag skips it.

Resolve this session's screenshot-subfolder id now (`rename-session.ps1 -GetId`, or `.sh --get-id`, which prints `<pid>-<procStart-ticks>`; never hand-roll it) and note two separate flags that must never collapse into one: whether this session captured any screenshots at all (the **zero-writes flag**) and whether any capture was actually put in front of Joe (the **shown-to-Joe flag**, true only if the transcript shows a frame reaching Joe, e.g. a `SendUserFile` call or `/preview`'s image branch, naming a screenshot tied to this change; PNGs merely existing under `.for_bepy/screenshots/<id>/` do not count). Why and how: `phase0-checks.md`.

**Visual-work check.** A `.css`/`.scss`/`.less` file, or any other user-facing visual/layout change, with the shown-to-Joe flag false: add "show Joe a live screenshot of the visual change" to the unfinished-commitments list below. A green headless/e2e pass is not a substitute (`phase0-checks.md`).

**Orphaned-probe check.** If the project has any file under a `verify/`, `e2e/`, `tests/`, `test/`, `__tests__/`, `cypress/`, `playwright/` or `spec(s)/` directory, run `python ~/.claude/tools/dead-probe-check.py --root <project root> --against HEAD`, and if `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'` resolves, also `--against '@{u}..HEAD'`. It never blocks (exit 0 always), but any finding is a real warning: add it to the unfinished-commitments list exactly like a visual-work item so it gets the same finish-or-file handling. Measurement and incident: `phase0-checks.md`.

Scan the full session for dev-stated commitments: every request the dev made, a single one-line ask included ("fix the typo"), plus explicit multi-part asks ("we need to do X, Y, Z"), a numbered plan the dev agreed to, and the visual-work item above if it triggered. A one-off request is the most common shape of a short session and the easiest to half-finish, so it is never exempt for having only one part. For each, check whether it actually got done by the time `/close` was invoked.

This is distinct from Phase 1 step 5 (Claude's own unexecuted "want me to...?" offers): this catches things the dev asked for, not things Claude proposed unprompted.

If everything the dev asked for was completed: proceed silently to Phase 1, no output from this phase.

Before asking anything below: search this project's memory for the subject first. If a memory entry already decides this exact fork (a past override, a standing preference for this kind of unfinished item), apply it directly and log which memory decided it, instead of asking again.

If the repo's own `CLAUDE.md` imports `~/.claude/snippets/full-auto.md` (check for the literal `@import` line), the Default branch below still applies, except that an item only the dev can unblock is filed as a `task` todo instead of asked, with one printed line naming it, e.g. `full-auto repo: filing "<item>" as a task todo instead of asking (repo imports full-auto.md)`.

**What counts as unfinished** (the only set the finish-first default acts on): (a) the dev-stated commitments from the scan above, (b) Claude's offers the dev explicitly accepted, (c) the visual-work and orphaned-probe items. Never in the set: Claude's un-accepted offers (Phase 1 step 5 files those), anything already filed as a todo (a deferred bundle is not reopened at close time), and a push the dev has not asked for. Size brake: an item that would reach beyond what the dev's message implied (files outside the original ask, a multi-step plan the dev only listed) is filed as a `task` todo instead, with one line saying so.

**In-flight background work** (a `run_in_background` Bash command, a background `Agent`, a `/loop` or pending `ScheduleWakeup` this session started) counts as unfinished too: wait for it in the foreground, one bounded call at a time (poll its output file or `ListAgents`, each call with an explicit `timeout`), never by ending the turn. Cap: after 30 minutes, or when `ListAgents` reports it lost or dead, stop waiting, file it as a `task` todo naming what was still running, and continue. A CI/release build watcher (`commit/build-watch.md`) is never waited on.

Branches, in order:

- **Unattended chain** (`/sleep-when-done`, autopilot, `/auto-do-todos`, `/loop-todos` cycles, `/respawn` and `/auto-respawn`'s `--dont-close` runs, any run with nobody to answer): never finish, never wait, never ask. File each unfinished item straight to Phase 3 as a `task` todo and continue.
- **`--now`**: file each unfinished item as a `task` todo, then continue. No finishing, no waiting.
- **Default** (a dev-typed `/close`, or the gate chat's trailing one): finish every item Claude can do alone, without asking, under every normal rule (testing floor, `/commit` per the auto-commit policy; this grants no push). For an item only the dev can unblock (a decision, a red check Claude cannot fix, a physical action), ask it and end the turn with status `question`: the close stays armed, and once the answer arrives and the work is done, continue at Phase 1 without being told again. A dev message that drops or redirects the work disarms it. In a gate chat this is what keeps a red gate from closing behind the dev's back: it closes only once the push landed.

No silent-drop path either way - every unfinished item either gets done now, or gets filed.

## Phase 1 - Retrospective

**Signal the start first.** Before anything else here, unless `--dont-close` was passed, call `close_session` with `stage: "started"` when that tool exists and its schema lists a `stage` parameter. It only marks the chat Closing and tears nothing down. If the tool has no `stage` parameter (an older host), skip the call: without it the call is the final teardown confirmation, which belongs to Phase 6 alone. In a plain terminal session the tool does not exist, so skip silently.

Scan the full session. Compute all bullets below internally every time - Phase 3 persists from them regardless of whether anything gets printed.

### Transcript grounding (long sessions only)

"The full session" means the raw transcript on disk, not just what is still in context: auto-compaction summarises early material away, exactly where corrections and hard-won facts live. Skip this entirely if the transcript is under ~500 lines. Otherwise resolve it and `Grep` it (never `Read` it whole) for the dev's own turns, per `skills/close/grounding.md` (also the recipe `/commit`'s Pre-push transcript check and `/zng-kickoff` use for the session's transcript path and `sessionId`).

### What to compute

1. **Detours.** Tool calls, file reads, or directions taken that turned out unneeded. Each = signal of missing context up front or wrong skill firing.
2. **Corrections.** Places the dev pushed back, rejected, or rewrote your output. What rule was missing or violated?
3. **Repeated manual steps.** Anything done 2+ times manually that should be a skill. List name + one-line scope. Candidate for a `skill-improvement` ai_todo (persisted in Phase 3). Do NOT draft the skill inline.
4. **Skill rule violations.** Active skills whose rules got broken. Pointer to skill + which rule. Candidate for a `skill-improvement` ai_todo (persisted in Phase 3). Enforcement gap, not a "be more careful" fix.
5. **Unfinished offers.** Scan the session for any "want me to...?" / "should I...?" / "next we could..." offer Claude made that did not get executed. Each is a candidate for a `task` ai_todo (persisted in Phase 3). List them as: `[file/target] - [action] - [reason]`.
6. **Verdict.** One sentence: was the session efficient, mid, or wasted effort? Pick one. No hedging.

### Print rule

Joe does not read this by default - it exists to feed Phase 3. Print the full bullet list ONLY if at least one of 1-4 has a real (non-"none") entry. If everything is empty, print nothing from Phase 1 and let Phase 4's one-line counter be the only visible trace of this phase. Never print "none" bullets just to show the work happened.

**Conductor-hosted chat (the `send_message` tool exists): print nothing, ever.** The bullet list is Phase 3's input, not a message, so no retrospective bubble reaches Joe from a clean close. Only a real miss is sent: one `send_message` line naming the miss, with `kind` `do_this` when Joe must act and `report` otherwise. A repeated manual step or a skill-rule violation that Phase 3 files as a todo is not a miss; a lost memory write, an unfinished item Joe asked for, or a failed step is.

## Phase 2 - Code Health Review

Skip this entire phase if ANY:

- `--skip-review` was passed.
- Zero code files changed this session (only docs/config/`.for_bepy/`/`.claude/todos/`/memory edits).
- Fewer than 50 added lines total across all code files (`git diff --shortstat` insertions). Small diffs are almost always edits to existing code, not new symbol declarations, so DRY/dead-code review finds nothing.

Scope arg: THIS session's own commits, never everything unpushed (a shared branch with concurrent sessions makes `unpushed` review other sessions' work; an in-session push makes it resolve empty). Full rules in `review-scope.md`; the short form:

- Sha(s) recalled from this conversation's own `/commit`/`git commit` calls: pass `shas:abc1234 def5678`. The prefix is required even for one sha (a bare lone sha is read as a range and diffs empty right after a commit).
- None recalled: `list_peers`. No other active session: `uncommitted`. One or more active: pass `files:<files this session edited, deduped>`; zero edits means skip Phase 2 and print why.
- Cannot determine this session's own commits at all (resumed/forked): SKIP Phase 2 and print why, never fall back to `unpushed`/`uncommitted`.

Invoke `/code-check` with that scope arg via the Skill tool. It handles the analysis and writes the todos directly. Read its summary line (`code-check: N findings ...`) to extract the finding count for the Phase 4 counter. It dispatches the analysis into a fresh subagent that did not write this session's code (its "The analysis runs in a fresh subagent, always" section): pass it the scope only, never what the session was trying to achieve and never a summary of the work, since the reasoning behind the code is exactly what must not travel.

## Phase 3 - Persist

Run in this order:

1. **Memory writes.** Read `~/.claude/refs/memory-rubric.md` first if it hasn't been read this session - it defines the ADD/UPDATE/DELETE/NONE gate, the bar for writing at all, and the evidence requirement. Then for each correction or non-obvious confirmation from Phase 1, route it through that gate and write to the store CLAUDE.md's Global Knowledge Vault section says it belongs in (vault for cross-project facts and people, native per-project Auto Memory for project-local ones), updating the relevant index. Skip if nothing qualifies; NONE is a normal outcome. Never invent memories to look productive.

   **Dedup against this session's own writes.** Memories written live earlier in this session are already covered - list them before evaluating, and treat a Phase 1 candidate matching one as NONE rather than writing a near-duplicate. The transcript sweep exists to catch what live capture MISSED, not to re-extract what it already got.
2. **`.claude/todos/`.** Peer sweep first: call `list_peers` once (the one unconditional call) before writing any `task` todo, since a live peer may already have picked the item up. Zero peers is a weak signal, never worded as "confirmed unstarted"; one or more: also `read_messages`, and where a peer's session name or message names the same ticket/file/feature, `post_message` to ask and fold the answer (or "asked, no reply yet") plus the sweep timestamp into that todo's Notes. An item whose fix lives in a DIFFERENT repo (most often a global `~/.claude` finding from a project session) is filed into THAT repo's backlog per `skills/create-todo/SKILL.md`'s "Cross-repo filing" flow. One `.md` file per item, from: Phase 0 unfinished items filed instead of finished (`**Type:** task`, `**Origin:** dev`); Phase 1 step 5 offers (`task`, `ai`); Phase 1 steps 3-4 (`skill-improvement`, `ai`, Approach names the skill file). Follow `ai-todos-format.md` for template (one-sentence `**Summary:**`), ids (`reserve-todo-id.ps1`, `pc-NNNN`) and git-policy self-heal; a future cold session must be able to execute the task from the file alone. Skip if no items; Phase 2 findings are written by `/code-check` directly, never re-written here. Full wording: `persist.md`.
3. **Screenshot summary.** `/close` never deletes screenshots (`/disk-doctor` ages them out). Count the files under this session's own `.for_bepy/screenshots/<pid>-<start-ticks>/` (the Phase 0 id) for Phase 4's counter: 0 if the zero-writes flag was true; if it was false but that subfolder is missing or empty, record `mismatch` instead of 0, and never substitute an mtime-matched folder. If the session used the Playwright MCP screenshot tool, also report (never delete) stray `.png` files in the repo root and `.playwright-mcp/`. `.for_bepy/mockups/` is `/mockup` step 7's. Details: `persist.md`.
4. **Session digest.** Skip a session with no decision or rejected option worth keeping. Otherwise pipe `## Done`, `## Decided`, `## Rejected` (option plus why it lost) and `## Open` sections (`none` under an empty one) to `python ~/.claude/skills/recall/recall.py digest-save <sessionId>` (resolve `<sessionId>` via `grounding.md` step 1 even if grounding was skipped; never pass `--replace`; no extra model call). Details: `persist.md`.
5. **Inherited respawn detail file.** If this session's first user message is a `/respawn` handoff naming a `Detail file: <path>.respawn.md`, delete that file; skip silently when there is none. Applies under `/respawn` too.

There is no implicit /commit step: if the dev wants a commit, they chain `/commit` (with whatever subcommand) into the /close call.

## Phase 4 - Counter summary

**Conductor-hosted chat (the `send_message` tool exists): do not send the counter.** Joe does not read the bookkeeping footer, so a clean close sends him nothing for this phase. Still compute the counts. Send one `send_message` line (`kind` `report`, or `do_this` when Joe must act) only for a counter item that is a real miss: a screenshot `mismatch`, a Phase 2 that could not run, or a Phase 3 write that failed. Name the miss and nothing else.

Otherwise (a plain terminal session) print one line, always - this is the one thing Joe reliably sees from Phases 1-3:

```
N memory writes . N todos written (M from review, K skill-improvement) . N screenshots written to <dir> . chain: <list of chained commands or "none"> . closing: yes/no
```

`M from review` is the count of findings from Phase 2 (size + DRY + dead code); if Phase 2 was skipped, omit the parenthetical and say `review skipped`. `K skill-improvement` is the subset of this close's todos tagged `skill-improvement` in Phase 3 step 2; omit `, K skill-improvement` if zero. `N screenshots written to <dir>` is Phase 3 step 3's count plus the subfolder path; if the count is 0, print `0 screenshots` and drop the `to <dir>` clause. If step 3 flagged `mismatch`, never print `0 screenshots`: print `screenshots: id mismatch, this session captured some but <dir> is missing - check .for_bepy/screenshots/ for the real folder`.

## Phase 5 - Run chained commands

Walk the parsed chain in user order. Invoke each via the `Skill` tool with its args. Wait for each to return before moving to the next. If any chained command fails (errors, hook rejection, etc.): stop the chain right there, run none of the rest, skip Phase 6 (failure means there may be unsaved state worth keeping the window open for), and print which command failed and why. No chained commands: skip this phase.

## Phase 6 - Close terminal

**Default: always run.** Skip only if ANY of these are true:

- `--dont-close` was passed.
- Any chained command in Phase 5 failed.
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, a Bash command with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.

**A CI/release build watcher (`commit/build-watch.md`) is the explicit non-blocker**: it never holds Phase 6 open, even mid-watch; closing kills it and that is accepted. **Supervised servers:** before stopping any `supervised-run` entry, call `list_peers` (a live peer may depend on it); default to leaving it running (`finish.md`).

If all clear: first, if the `close_session` MCP tool is available (Conductor-hosted), call it once, the host's authoritative teardown confirmation (the session ends and its process is killed at turn completion). Never make this final call if any skip condition applies (the Phase 1 `stage: "started"` signal is separate); skip it silently in a plain terminal.

**HARD ORDERING RULE:** running the rename/kill script WITHOUT having called `close_session` first, where that tool exists, leaves Conductor chats permanently un-closed (the daemon respawns the process every turn; only the tool call ends the chat). If `close_session` is in your tool list, the script line is FORBIDDEN until the tool call has returned. The script enforces this: in an SDK-hosted session (`CLAUDE_CODE_ENTRYPOINT` starting `sdk-`) `-Close` refuses with exit 3 and `REFUSED: host-managed session`; seeing that means the call was skipped, make it now. `-Force` / `--force` exists only for an SDK host with no `close_session` tool.

Otherwise (a plain terminal), run for your OS (literal paths; dynamic `$env:` expressions fail the permission matcher):

**Mac/Linux:**
```sh
sh /Users/josipmuzic/.claude/skills/close/rename-session.sh --close
```

**Windows:**
```powershell
& "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Close
```

The script kills the claude ancestor process after an 800ms delay so this final response flushes first. If kill was skipped, print on its own line: `Terminal kept open. Run /clear or close manually.` for `--dont-close`, else `Exit skipped: <reason>. Run /clear or close manually.`

## Anti-patterns

- Performative "session went well" output. If retrospective bullets are all "none", say so plainly: "Session was clean, nothing to log." Do not pad.
- Drafting new skills inline. /close surfaces candidates, /bepy-skill-creator builds them.
- Auto-committing without `/commit` in the chain. Dev opts in explicitly now.
- Writing memories about ephemeral session state. Re-read auto-memory rules before writing.
- Trying to invoke `/exit` as a skill or chained command. Terminal kill is built into Phase 6 by default.
- Promising to run /close later, or ending a turn to wait for background work. If the dev asked for it, Phase 0 finishes and waits in the foreground, and the phases run in that same turn.
- Firing on a mention. Only a `/close` that starts or ends the dev's own message is a trigger.
