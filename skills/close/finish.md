# /close Phase 6: close the terminal (full procedure)

Read on demand from `skills/close/SKILL.md` Phase 6 for the host-managed and plain-terminal details, the build-watcher and supervised-server rules.

**Default: always run.** Skip only if ANY of these are true:

- `--dont-close` was passed.
- Any chained command in Phase 5 failed.
- Any background work is still running in this session: spawned `Agent` with `run_in_background: true`, a Bash command with `run_in_background: true`, active `/loop`, or pending `ScheduleWakeup`. Check before killing.

**Explicit non-blocker: a CI/release build watcher.** `commit/build-watch.md`'s watcher (launched after `/commit push`/`/release`) does NOT count as background work above and must NEVER hold Phase 6 open, even mid-watch. It is fire-and-forget by design - the dev checks the result later via `gh run list`/GitHub directly, not by keeping this terminal alive. Closing kills the watcher process; that is accepted, not a bug. Proceed through Phase 6 normally regardless of watcher state.

**Supervised servers.** If wrapping up this session means stopping any `supervised-run` entry, call `list_peers` first - see that skill's Stop step. A live peer in the same repo may be depending on it as shared infra, not this session's own orphan; default to leaving it running and saying so instead of stopping it. A port still answering a probe after the process dies is not proof anything is alive (2026-09-01, zng-app incident).

If all clear: first, if the `close_session` MCP tool is available (Conductor-hosted session), call it once - this is the host's authoritative teardown confirmation, so the session ends and its process is killed at turn completion. Never make this final call if any skip condition above applies (the Phase 1 `stage: "started"` signal is separate and only marks Closing); skip it silently in a plain terminal session where the tool doesn't exist.

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
