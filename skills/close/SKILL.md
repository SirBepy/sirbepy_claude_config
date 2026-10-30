---
name: close
description: Retrospect, review, persist, close. Fires on /close as a message's first or last word; finishes open work first.
argument-hint: "[task text] [--now] [--dont-close] [--skip-review] [--light] [/commit ...] [/sleep-when-done]"
---

# /close

> Retrospect, review, persist, close terminal.

## Usage

```
/close                                  # finish open work, then retrospect + review + persist + close terminal
fix the typo /close                     # do the task first, then the same as /close
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

### Trigger

Fires only on a `/close` token the dev typed as the first or last word of their own message, or that
ends a gate chat's spawn prompt (which carries the dev's push request). Text before a trailing
`/close` is a task to finish first (`fix the typo /close`); any other `/command` in it runs as part
of that task, per `~/.claude/refs/slash-arg-parsing.md`. Claude Code only expands a slash command at
the very start of a prompt, so a trailing token arrives as plain text and Claude loads this skill
through the Skill tool itself; that is why the skill stays model-invocable. Never a trigger: `/close`
mid-sentence, inside quotes, code, tool output or skill text, negated or conditional ("don't /close
yet", "should I /close?"). If Claude cannot point at the dev's own message ending or starting with the
token, it does not start. Claude also runs it unprompted under CLAUDE.md's "Task done, no question
pending: run /close yourself"; that path has nothing in flight by definition, so it never waits.

If `--light` is passed: read `close/light.md` before proceeding. It overrides Phases 1-3 with high-context-mode versions.

Remaining args follow the chaining convention in `~/.claude/refs/slash-arg-parsing.md`: each is a
chain of slash commands, and each slash command may be followed by its own positional args (anything
until the next `/`). Empty remaining args = bare /close (retrospect + persist, then close unless
--dont-close).

Examples:

- `/close /release` → dont-close: false, chain: `[/release]`
- `/close --dont-close /commit v` → dont-close: true, chain: `[/commit v]`
- `/close /sleep-when-done` → dont-close: false, chain: `[/sleep-when-done]`

## Role

Honest reviewer, not cheerleader. Same anti-sycophancy bar as /rate-it. If session was sloppy, say so. No silver linings, no "great work today".

## When to run

The dev triggers /close (see Trigger above), or Claude runs it when a task is done with nothing pending. Never auto-fire on token thresholds: deciding "this session is done" is what makes the retrospective land.

Phase 0 starts in the SAME turn /close is invoked, and Phases 1-5 run in that same turn once Phase 0's finishing and waiting are done. Never end a turn to wait for background work to re-invoke the session: on 2026-08-19 a /close that promised to run "once it returns" ended its turn with zero phases, the host marked the chat done, and the retrospective was nearly lost (`.claude/todos/done/close-must-not-be-deferred-behind-background-work.md`). Persistence is the point of this skill, so it cannot hang on optional work forever: Phase 0's wait is in the foreground and capped.

## Host app integration (Claude Conductor)

When this session is hosted by Claude Conductor (claude_usage_in_taskbar), the host handles the "Closing" row state and the teardown itself - no text markers:

- **Closing state:** the host marks the row "Closing" automatically the moment a `/close` turn starts (it sees the prompt began with `/close`). Nothing to emit for this.
- **Teardown:** confirmed by calling the `close_session` MCP tool in Phase 6 (see below), NOT by any text output. The host then ends the session and kills the process at turn completion.

If the `close_session` tool isn't available (a plain terminal session not hosted by Conductor), just skip it - the Phase 6 script still closes the terminal as usual. Never emit `<cc-close:*>` text markers; they're retired.

## Phase 0 - Safe-to-close check

Runs first, before Phase 1, every time - no flag skips it.

Resolve this session's screenshot-subfolder id now: run `rename-session.ps1 -GetId` (or `.sh
--get-id`), which prints `<pid>-<procStart-ticks>` - resolved via `$env:CLAUDE_CODE_SESSION_ID`
matched against `~/.claude/sessions/*.json`, not a process-tree walk (todo 60: the walk resolved
to two different PIDs at two points in the SAME session; the sessionId match is stable). The
start-time suffix is load-bearing, not decoration: Windows recycles PIDs, so a bare PID can
collide with a dead session that left files behind; PID plus start time cannot. Also note two
separate flags, which answer different questions and must never collapse into one: whether this
session captured any screenshots at all (the **zero-writes flag**), and whether any capture was
actually put in front of Joe (the **shown-to-Joe flag**, see the visual-work check below). Phase 3
step 3 uses the id and the zero-writes flag only: the id locates this session's own subfolder for
Phase 4's screenshot count, and the zero-writes flag sets that count to 0 without touching the
filesystem.

**Visual-work check.** If any file changed this session matches `.css`/`.scss`/`.less`, or is otherwise a user-facing visual/layout change, and the shown-to-Joe flag above is false, add "show Joe a live screenshot of the visual change" to the unfinished-commitments list below. The shown-to-Joe flag is true only if the transcript shows a frame actually reaching Joe this session - a `SendUserFile` call, `/preview`'s image branch, or equivalent - naming a screenshot tied to this change; it is NOT satisfied by files merely existing under `.for_bepy/screenshots/<id>/`. A `/e2e` or `/flutter-e2e` run (or any other automated harness) writes PNGs there that nobody ever looks at - that sets the zero-writes flag false while the shown-to-Joe flag stays false too, and it is the shown-to-Joe flag this check must read (todo 1027: a session that ran `pnpm run test:view` had the zero-writes flag read FALSE from 29 harness-written PNGs and the check never fired, though Joe saw none of them). CLAUDE.md's UI & visual changes section already requires this; a green headless/e2e test pass is not a substitute, since it cannot detect "this looks wrong" (2026-08-01: an AUQ card-height CSS fix shipped on a passing Playwright regression test alone, never shown live).

**Orphaned-probe check (todo 968).** If this project has any file under a `verify/`, `e2e/`,
`tests/`, `test/`, `__tests__/`, `cypress/`, `playwright/`, or `spec(s)/` directory, run
`python ~/.claude/tools/dead-probe-check.py --root <project root> --against HEAD` (uncommitted
changes), and if `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'` resolves, also run it
`--against '@{u}..HEAD'` (this session's unpushed commits). It greps removed `title=`/`aria-label=`
(colon-truncated) and `id=`/`data-testid=`/`name=` (exact) literals against those directories for
a selector a deleted or renamed UI surface left dangling - no browser, seconds not minutes. Exists
because `/e2e` is deliberately opt-in per CLAUDE.md's testing floor, so nothing else re-checks a
tracked probe after the surface it drives changes; the incident (five commits shipped "verified"
on a dead `title^="Projects:"` selector, caught only because the dev happened to run `/e2e` by
hand) is in the todo file. Exits 0 always - it never blocks - but any finding it prints is a real
warning, not noise: it was measured against 143 real commits before being wired in and produced
exactly one hit, the one real incident, zero false positives (a bare-word version of the same idea
measured 9 false positives to 1 true positive on the same corpus and was rejected for that). Add
any finding to the unfinished-commitments list below exactly like a visual-work item, so it goes
through the same Phase 0 finish-or-file handling rather than getting silently
dropped if nobody reads the raw script output.

Scan the full session for dev-stated commitments: every request the dev made, a single one-line ask included ("fix the typo"), plus explicit multi-part asks ("we need to do X, Y, Z"), a numbered plan the dev agreed to, and the visual-work item above if it triggered. A one-off request is the most common shape of a short session and the easiest to half-finish, so it is never exempt for having only one part. For each, check whether it actually got done by the time `/close` was invoked.

This is distinct from Phase 1 step 5 (Claude's own unexecuted "want me to...?" offers) - this catches things the dev asked for, not things Claude proposed unprompted.

If everything the dev asked for was completed: proceed silently to Phase 1, no output from this phase.

Before asking anything below: search this project's memory for the subject first. If a memory entry already decides this exact fork (a past override, a standing preference for this kind of unfinished item), apply it directly and log which memory decided it, instead of asking again.

If the repo's own `CLAUDE.md` imports `~/.claude/snippets/full-auto.md` (check for the literal `@import` line - mechanical detection, not a guess about repo ownership), the Default branch below still applies, except that an item only the dev can unblock is filed as a `task` todo instead of asked, with one printed line naming it, e.g. `full-auto repo: filing "<item>" as a task todo instead of asking (repo imports full-auto.md)`. This repo opted out of being asked.

**What counts as unfinished** (the only set the finish-first default acts on): (a) the dev-stated commitments from the scan above, (b) Claude's offers the dev explicitly accepted, (c) the visual-work and orphaned-probe items. Never in the set: Claude's un-accepted offers (Phase 1 step 5 files those), anything already filed as a todo (a deferred bundle is not reopened at close time), and a push the dev has not asked for. Size brake: an item that would reach beyond what the dev's message implied (files outside the original ask, a multi-step plan the dev only listed) is filed as a `task` todo instead, with one line saying so.

**In-flight background work** (a `run_in_background` Bash command, a background `Agent`, a `/loop` or pending `ScheduleWakeup` this session started) counts as unfinished too: wait for it in the foreground, one bounded call at a time (poll its output file or `ListAgents`, each call with an explicit `timeout`), never by ending the turn. Cap: after 30 minutes, or when `ListAgents` reports it lost or dead, stop waiting, file it as a `task` todo naming what was still running, and continue. A CI/release build watcher (`commit/build-watch.md`) is never waited on.

Branches, in order:

- **Unattended chain** (`/sleep-when-done`, autopilot, `/auto-do-todos`, `/loop-todos` cycles, `/respawn` and `/auto-respawn`'s `--dont-close` runs, any run with nobody to answer): never finish, never wait, never ask. File each unfinished item straight to Phase 3 as a `task` todo and continue.
- **`--now`**: file each unfinished item as a `task` todo, then continue. No finishing, no waiting.
- **Default** (a dev-typed `/close`, or the gate chat's trailing one): finish every item Claude can do alone, without asking, under every normal rule (testing floor, `/commit` per the auto-commit policy; this grants no push). For an item only the dev can unblock (a decision, a red check Claude cannot fix, a physical action), ask it and end the turn with status `question`: the close stays armed, and once the answer arrives and the work is done, continue at Phase 1 without being told again. A dev message that drops or redirects the work disarms it. In a gate chat this is what keeps a red gate from closing behind the dev's back: it closes only once the push landed.

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

Determine scope arg - identify THIS session's own commits, never everything unpushed (a shared
branch with concurrent sessions makes `unpushed` review other sessions' work; an in-session push
makes it resolve empty - two symptoms of one root cause):

- Recall every sha THIS session's own `/commit`/`git commit` calls produced earlier in this
  conversation (each reports its sha on success) - never re-derive from `git log` timestamps or
  `@{u}..HEAD`, both of which conflate concurrent sessions or go empty post-push.
- Zero recalled: call `list_peers`. No other active session on this worktree: pass `uncommitted`
  (unchanged - covers working-tree-only changes). One or more active: `uncommitted` has no sha to
  filter by, so a peer's dirty files enter scope unattributed (2026-08-31,
  claude_usage_in_taskbar - 5 own files plus 5 peer files, zero commits made). Pass the file list
  THIS session itself edited or wrote this turn (already known from its own Edit/Write calls in
  context, deduped) with a `files:` prefix instead, e.g. `files:a.ts b.ts` - same attribution
  problem `shas:` already solves for the commit branch, applied where there's no sha to filter by.
  If this session made zero edits at all, skip Phase 2 and print why rather than passing an empty
  scope.
- One or more recalled: pass the list as the scope arg with a `shas:` prefix, e.g.
  `shas:abc1234 def5678`. The prefix is required even for a single sha: a bare lone sha is read
  as a range and diffs sha-to-working-tree, which is empty right after a commit. `/code-check`
  resolves it to the union of files each commit touched, reviewing exactly this session's commits
  regardless of push state or how many other sessions share the branch.
- Can't determine this session's own commits at all (e.g. resumed/forked, no commit history
  visible in context): SKIP Phase 2 and print why, rather than falling back to
  `unpushed`/`uncommitted` and silently reviewing the wrong scope.

Invoke `/code-check` with that scope arg via the Skill tool. It handles the analysis and writes the todos directly. Read its summary line (`code-check: N findings ...`) to extract the finding count for the Phase 4 counter.

`/code-check` dispatches the analysis itself, into a subagent that did not write this session's code - see its "The analysis runs in a fresh subagent, always" section. Do not pass it what this session was trying to achieve, and do not summarise the work for it. Scope is the only input it gets from here; the reasoning behind the code is exactly what must not travel.

## Phase 3 - Persist

Run in this order:

1. **Memory writes.** Read `~/.claude/refs/memory-rubric.md` first if it hasn't been read this session - it defines the ADD/UPDATE/DELETE/NONE gate, the bar for writing at all, and the evidence requirement. Then for each correction or non-obvious confirmation from Phase 1, route it through that gate and write to the store CLAUDE.md's Global Knowledge Vault section says it belongs in (vault for cross-project facts and people, native per-project Auto Memory for project-local ones), updating the relevant index. Skip if nothing qualifies; NONE is a normal outcome. Never invent memories to look productive.

   **Dedup against this session's own writes.** Memories written live earlier in this session are already covered - list them before evaluating, and treat a Phase 1 candidate matching one as NONE rather than writing a near-duplicate. The transcript sweep exists to catch what live capture MISSED, not to re-extract what it already got.
2. **`.claude/todos/`** Peer sweep first, conditional on concurrent sessions: before writing any
   `task` todo below, call `list_peers` once - the one unconditional call, cheap even solo. Phase 0
   and Phase 1 step 5 are the two sources that assert work is unstarted or unfinished, and a live
   peer may already have picked one up (todo 890: a `/handoff` todo called two Shortcut items
   unstarted while a peer had already fixed and shipped both). Zero peers: add nothing and write the
   todos below as-is - `list_peers` returning zero is a weak signal, not proof of solitude, it has
   undercounted a live peer in this repo before, so an empty sweep is never worded as "confirmed
   unstarted". One or more peers: also call `read_messages`, check whether a peer's session name or
   a recent message names the same ticket/file/feature as the item about to be filed, and where it
   does `post_message` to ask directly, folding the answer (or "asked, no reply yet") plus the
   sweep's timestamp into that todo's Notes instead of filing it as plain unstarted work.

   An item whose fix lives in a DIFFERENT repo (most often a finding about the global `~/.claude`
   tree surfaced from a project session) is filed into THAT repo's backlog, per root `CLAUDE.md`'s
   allocation rule. Follow `skills/create-todo/SKILL.md`'s "Cross-repo filing" flow rather than
   hand-rolling it: the destination gets the same content-duplicate guard, the same atomic id
   reservation, and the same `.git/info/exclude` self-heal a local file gets.

   Write a separate `.md` file per item from:
   - Phase 0 (unfinished items filed instead of finished: `--now`, an unattended chain, the size brake, or the wait cap) - tag `**Type:** task`,
     `**Origin:** dev` (the dev asked for it; Claude just didn't finish it in time).
   - Phase 1 step 5 (unfinished offers) - tag `**Type:** task`, `**Origin:** ai` (Claude proposed it
     unprompted and it never got executed).
   - Phase 1 steps 3-4 (repeated manual steps, skill rule violations) - tag `**Type:**
     skill-improvement`, `**Origin:** ai`, Approach section names the skill file involved.

   Follow `ai-todos-format.md` (this skill's folder) for everything: template (every todo gets a one-sentence `**Summary:**`, plus a `## Why` only when the session states the reason), filename/id rules (`<id>-<slug>.md`, id from `reserve-todo-id.ps1`, `pc-NNNN` form), git-policy self-heal. The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items. Note: Phase 2 review findings are written to the backlog by `/code-check` directly - do not re-write them here.
3. **Screenshot summary.** `/close` no longer deletes screenshots - todo 324 moved that to
   `/disk-doctor`, which ages folders out later while Joe decides. If Phase 0 recorded any
   screenshots captured this session, count the files under this session's own
   `.for_bepy/screenshots/<pid>-<start-ticks>/` subfolder (the Phase 0 id) for Phase 4's counter. 0
   if Phase 0's zero-writes flag was true. If that flag is FALSE (this session did capture
   screenshots) but the Phase-0 id's subfolder is missing or empty, that is an id mismatch (todo
   459: `-GetId` can still resolve to an id nobody wrote to), not a real zero - flag it as
   `mismatch` for Phase 4 instead of counting 0. Never substitute an mtime-matched folder here; the
   ownership proof is by subfolder name only (Phase 0), since a concurrent session's files can be
   newer or older. Nothing is printed or deleted here. If
   this session captured any screenshot via the Playwright MCP
   (`mcp__playwright__browser_take_screenshot`), also check the repo root and `.playwright-mcp/`
   for stray `.png` files - the MCP writes there directly and this summary cannot see them; report
   any found, never auto-delete, since they may be git-tracked. `.for_bepy/mockups/` and
   `mockup-step-*.json` are out of scope here too - `/mockup` step 7 owns their disposal.
4. **Session digest.** Skip a session with no decision or rejected option worth keeping (a pure
   mechanical run). Otherwise write this session's digest from the Phase 1 material, no extra
   model call: pipe `## Done`, `## Decided`, `## Rejected` (option plus the reason it lost) and
   `## Open` sections (write `none` under an empty one) to
   `python ~/.claude/skills/recall/recall.py digest-save <sessionId>`. Resolve `<sessionId>` with
   Transcript grounding step 1 even when the rest of grounding was skipped as a short session,
   since a short session can still hold a decision worth a digest. It refuses to overwrite an existing digest; never pass
   `--replace` here. Digests feed `recall.py decisions` (design: `refs/permanent-memory.md`).
5. **Inherited respawn detail file.** If this session's first user message is a `/respawn`
   handoff naming a `Detail file: <path>.respawn.md`, delete that file: it was written only for
   this chat (`skills/respawn/SKILL.md` Step 1). Skip silently when there is none or it is already
   gone. Under `/respawn` this runs too, because the new detail file it writes next supersedes it.
Note: there is no implicit /commit step anymore. If the dev wants a commit, they chain `/commit` (with whatever subcommand they want) into the /close call.

## Phase 4 - Counter summary

Print one line, always - this is the one thing Joe reliably sees from Phases 1-3:

```
N memory writes . N todos written (M from review, K skill-improvement) . N screenshots written to <dir> . chain: <list of chained commands or "none"> . closing: yes/no
```

`M from review` is the count of findings from Phase 2 (size + DRY + dead code). If Phase 2 was skipped, omit the parenthetical and say `review skipped`. `K skill-improvement` is the subset of this close's todos tagged `skill-improvement` in Phase 3 step 2; omit `, K skill-improvement` if zero. `N screenshots written to <dir>` is Phase 3 step 3's count plus this session's subfolder path, so the folder stays discoverable; if the count is 0, print `0 screenshots` and drop the `to <dir>` clause. If Phase 3 step 3 flagged `mismatch`, never print `0 screenshots` - print `screenshots: id mismatch, this session captured some but <dir> is missing - check .for_bepy/screenshots/ for the real folder` instead, so the loss stays visible rather than reading as a clean close. `/close` never deletes screenshots - `/disk-doctor` reclaims that space later, by age (todo 324).

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
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, a Bash command with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.

**Explicit non-blocker: a CI/release build watcher.** `commit/build-watch.md`'s watcher (launched after `/commit push`/`/release`) does NOT count as background work above and must NEVER hold Phase 6 open, even mid-watch. It is fire-and-forget by design - the dev checks the result later via `gh run list`/GitHub directly, not by keeping this terminal alive. Closing kills the watcher process; that is accepted, not a bug. Proceed through Phase 6 normally regardless of watcher state.

**Supervised servers.** If wrapping up this session means stopping any `supervised-run` entry, call `list_peers` first - see that skill's Stop step. A live peer in the same repo may be depending on it as shared infra, not this session's own orphan; default to leaving it running and saying so instead of stopping it. A port still answering a probe after the process dies is not proof anything is alive (2026-09-01, zng-app incident).

If all clear: first, if the `close_session` MCP tool is available (Conductor-hosted session), call it once - this is the host's authoritative teardown confirmation, so the session ends and its process is killed at turn completion. Never call it if any skip condition above applies; skip it silently in a plain terminal session where the tool doesn't exist.

**HARD ORDERING RULE:** running the rename/kill script WITHOUT having called `close_session` first, in a session where that tool exists, leaves Conductor chats permanently un-closed - killing the process is MEANINGLESS to the daemon, it respawns the process every turn, so only the tool call actually ends the chat. If `close_session` is in your tool list, the script line below is FORBIDDEN until the tool call has returned.

**The script enforces this itself.** In an SDK-hosted session (`CLAUDE_CODE_ENTRYPOINT` starting `sdk-`, which a Conductor chat reports as `sdk-cli`) `-Close` refuses with exit 3 and a `REFUSED: host-managed session` line instead of killing. Once `close_session` has returned, the script is not needed at all: the host ends the process at turn end. Seeing that `REFUSED` line before `close_session` was called means the call was skipped - make it now. `-Force` / `--force` exists only for an SDK host with no `close_session` tool.

Otherwise (a plain terminal), run for your OS (literal paths hardcoded - dynamic `$env:` expressions fail the harness permission matcher and cause per-invocation prompts):

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
- Promising to run /close later, or ending a turn to wait for background work. If the dev asked for it, Phase 0 finishes and waits in the foreground, and the phases run in that same turn.
- Firing on a mention. Only a `/close` that starts or ends the dev's own message is a trigger.
