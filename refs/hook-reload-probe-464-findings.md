# Hook mid-session reload probe (todo 464), 2026-09-10

Claude Code version: 2.1.261. Method: nested `claude -p` sessions with an isolated scratch
project (`C:/tmp/hook-probe-464/project`, `--setting-sources project` so user-level
`~/.claude/settings.json` was never read, `--permission-mode bypassPermissions` so the scratch
run needed no permission prompts). The live `~/.claude/settings.json` was never touched
(`git diff -- settings.json` empty throughout). Each probe hook only blocks when its trigger
action targets a specific decoy filename (or, for Bash, contains a specific marker string), so
the settings.json edits used to wire/unwire hooks never risk being blocked by the hook they are
wiring - no deadlock risk. `--output-format stream-json --include-hook-events` captured every
`hook_started`/`hook_response` system event plus the final `permission_denials` list, so
"fired" is read off the raw transcript, not the model's paraphrase.

Two nested runs, both within a SINGLE process/session (the only way to test a live-process
reload, as opposed to a fresh process that would trivially read current disk state):

- RUN 1: PreToolUse(Bash) -> PreToolUse(Write) -> PreToolUse(Edit) -> PostToolUse(Write) ->
  Stop, each wired mid-session, triggered, then unwired before the next.
- RUN 2: PostToolUse(Write) FIRST (to rule out "only reloads after several prior edits"), then
  PreToolUse(Write), then PreToolUse(Bash) - reversed order from RUN 1 for the two events with
  a known-live-session-observed disagreement (2026-08-21 incident).

## Results

| Event | Verdict | How established | Evidence |
|---|---|---|---|
| PreToolUse: Bash | **Reloads live**, reliably, order-independent | Probed directly, 2 trials (RUN1 position 1, RUN2 position 3) | Both runs: `hook_response` `exit_code:2`, `stderr:"PROBE-FIRED-BASH"`, and the tool call appears in the final `permission_denials` list |
| PreToolUse: Write | **Reloads live**, reliably, order-independent | Probed directly, 2 trials (RUN1 position 2, RUN2 position 2) | Same evidence shape, `PROBE-FIRED-WRITE`, both runs |
| PreToolUse: Edit | **Reloads live**, reliably | Probed directly, 1 trial (RUN1 position 3) | `hook_response` `exit_code:2`, `stderr:"PROBE-FIRED-EDIT"`, in `permission_denials`. Not re-tested at a different position; inferred low-risk from Bash/Write's order-invariance since it is the same PreToolUse mechanism |
| PreToolUse: PowerShell | Reloads live | Not re-probed this session - already established from the real 2026-08-21 live-session incident (todo 419 correction, `destructive-command-guard.py` denied the orchestrator's own commands minutes after being wired) | Historical, cited not reproduced |
| PostToolUse: Write | **Reloads live, but with inconsistent/lagged timing** - do not assume it fires on the very next matching action | Probed directly, 2 trials | RUN1: wired at step 13, did NOT fire on the very next Write (step 14, target file matched); only showed a `hook_started`/`hook_response` (exit 0, no match since target was `settings.json`) on step 15, one call later. RUN2: wired at step 1, DID fire on that same wiring call's own completion and again on the immediate next Write. Net: the hook is invoked (proof it is not a startup-only snapshot) but the trial-1 gap shows the invocation does not always keep pace with the very next tool call - a periodic/debounced re-read is the best-fit explanation, not proven |
| Stop | **Did not fire** in the one trial run | Probed directly, 1 trial (RUN1, wired + armed as the last two steps before the session's only natural stop point) | No `hook_started`/`hook_response` for `Stop` anywhere in the transcript, no forced continuation, `terminal_reason:"completed"`, `stop_reason:"end_turn"`. Only one trial exists because a `-p` invocation's agentic tool loop only has one true Stop-triggering point (the very end); "position" doesn't vary the same way it does for Pre/PostToolUse |

## Discrepancy with the 2026-08-21 live-session incident

That incident is the origin of todo 464 and states "Write/Edit did NOT reload" for a PreToolUse
guard (`sensitive-file-guard.py`) wired at the same time as a Bash guard that did reload. This
probe's clean, isolated result is the opposite for PreToolUse specifically: Write and Edit both
reloaded live, exactly like Bash, in both an isolated single-hook scratch config and across two
orderings. **Not reconciled here** - candidates, unverified: a Claude Code version difference
(unknown which version the 2026-08-21 session ran), the live settings.json's far larger existing
hook set (15+ PreToolUse entries at once vs this probe's one), or a bug specific to that one
guard script rather than event-type behavior. Whatever the cause, the event *type*
(PreToolUse/PostToolUse/Stop) is not itself sufficient to predict "did not reload" for
Write/Edit - this probe shows PreToolUse Write/Edit CAN reload, so a future session that sees a
mid-session PreToolUse edit apparently not take effect should suspect the specific hook/config,
not assume the event type is snapshot-only.

## Practical consequence for todos 426/427/434/440

- A PreToolUse guard (any matcher tested: Bash, Write, Edit) wired mid-session by a session whose
  own commands would be denied can deadlock that session immediately - "wire it last" still holds
  and is now demonstrated, not just theorized.
- A PostToolUse guard is not a safe way to avoid that deadlock risk on the assumption "it won't
  reload" - it does reload, just with observed timing jitter of up to one intervening tool call
  in this trial.
- A Stop guard wired mid-session, in this one trial, did not take effect before the session's own
  natural end. Not enough trials to call this reliable; do not depend on it either way without a
  repeat probe.

## Gaps / what remains unverified

- PreToolUse:Edit was not re-tested at a second position (time/cost budget); its order-invariance
  is inferred from Bash and Write, not directly shown.
- PostToolUse was only tested with a `Write` matcher; other matchers not probed.
- Stop has only one trial; the lag pattern seen on PostToolUse raises the possibility that Stop
  could also reload with a longer lag than one `-p` invocation's short runtime can expose. A
  longer-lived nested session (multiple `--resume` turns with real elapsed time between) would be
  needed to rule that out; not attempted here.
- The 2026-08-21 discrepancy above is not reconciled, only flagged.
- Notification and SubagentStop/other events were out of scope per the todo's own Approach list
  and were not probed.

## Raw evidence location

Full transcripts (`run1-output.jsonl`, `run2-output.jsonl`, prompts, probe scripts) were captured
under `C:\tmp\hook-probe-464\` during this session and deleted afterward per the dispatch's
scratch-cleanup expectation; the quoted `hook_response`/`permission_denials` fragments above are
copied verbatim from that transcript before deletion.
