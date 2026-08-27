<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=5, reconfirm-count=1, content-hash=388b488c -->
<!-- duplicate-checked -->
# Six of ~30 hook events are wired, and all 41 hooks use exit codes only

**Type:** task
**Origin:** ai

## Goal

Wire the three hook events that would actually earn their place, and start using the JSON control
fields that make a hook do things an exit code cannot.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). Reference
implementation for every item below is `repos/disler_claude-code-hooks-mastery/dot-claude/hooks/`,
which wires 13 events with working code.

Current state: 6 event types wired (Notification, PreToolUse with 11 matchers, SessionEnd,
SessionStart, Stop, UserPromptSubmit), against roughly 30 available. All 41 hooks communicate purely
via exit codes and stdout prints.

**Events worth wiring, in value order:**

1. **`PreCompact`** - fires before manual or automatic compaction. `disler`'s `pre_compact.py` backs
   up the transcript. This is cheap insurance that does not exist here at all, and it matters because
   an existing memory entry records that task output files are cleared on completion and must be
   persisted on arrival. Compaction is the same class of loss with no current mitigation.
2. **`PermissionRequest`** - fires when the permission dialog is shown, **before** PreToolUse guards
   run, so it is structurally earlier than every existing guard. `disler`'s handler auto-allows
   whitelisted read-only ops or denies with a message. This serves a standing goal directly: there is
   a whole skill (`fewer-permission-prompts`) about reducing prompts, and this is the native
   mechanism for it. `TheoBrigitte/claude-config` also uses it for desktop notification on any
   permission prompt.
3. **`PostToolUse` (generic)** - the only PostToolUse hook here is the impeccable UI detector, and it
   lives in the untracked `settings.local.json` (see todo 415). `disler` runs validators after edits
   (`validators/{ruff,ty}_validator.py`); `poshan0126` auto-runs the matching test file for an edited
   source file, silent on pass, and auto-formats via the detected project formatter.

Lower value, listed so they are not rediscovered: `PostToolUseFailure` (structured error log, useful
for debugging guards), `Setup` (env persistence via `CLAUDE_ENV_FILE`, `additionalContext`
injection), `SubagentStart` and `SubagentStop` (Agent notifications already cover completion).

**JSON control fields not in use anywhere:**

- `hookSpecificOutput.additionalContext` - inject text into context without relying on a
  stdout-print convention. Every hook here prints and hopes.
- `decision.behavior: "allow"|"deny"` plus `updatedInput` on PermissionRequest - **can rewrite tool
  arguments before approval**, not merely approve or deny. Nothing here can do this.
- PostToolUse `"decision": "block"` - re-prompts Claude with a `reason` after a tool already ran, so
  results get validated rather than only prevented.
- Stop and SubagentStop `"decision": "block"` plus `reason` to force continuation. The em-dash and
  ui-screenshot Stop hooks only ever use exit code 2, which is a blunter version of the same thing
  with no structured reason.
- Global `"continue": false` with `"stopReason"` - the highest-priority override, beating both exit
  code 2 and `decision`. Unused.
- `suppressOutput: true` - hides stdout from the transcript.

The `Stop` + `decision: block` field is what todo 427 depends on, so read that one alongside this.

## Approach

1. Verify the event names and field names against the live harness before building anything. This
   list came from a third-party repo plus docs, and hook APIs move. `disler`'s working code is
   evidence the events exist somewhere, not that they exist in this version. **Confirm first, per the
   unverified-mechanism rule.**
2. Wire `PreCompact` first. It is the lowest-risk (pure observation, blocks nothing) and highest
   insurance value. Back the transcript up somewhere `/disk-doctor` can age out, following the
   session-id convention resolved via `close/rename-session.ps1 -GetId`, never a hand-rolled path.
3. Wire `PermissionRequest` second, and scope it narrowly at first: auto-allow a small explicit
   read-only allowlist, nothing more. Note that memory records `settings.local.json` carries extra
   permission allows and that `/fewer-permission-prompts` exists; check both before adding a third
   mechanism that overlaps them.
4. For the JSON fields, do not retrofit all 41 hooks. Pick the one case where the structured form is
   clearly better than exit code 2 and convert only that: the em-dash Stop hook is the candidate,
   since `"decision": "block"` with a `reason` gives Claude the actual offending line instead of a
   bare failure. Measure whether that changes behavior before converting others.
5. Fixture tests for each new hook, matching the existing convention.

## Acceptance

- Each wired event is proven to fire with real observed output, not assumed from documentation.
- `PreCompact` produces a transcript backup at a path resolved via the session-id script, verified by
  listing the file.
- `PermissionRequest`'s allowlist is narrow and enumerated; a non-allowlisted operation still prompts.
- If the em-dash hook is converted to `"decision": "block"`, its existing test still passes and the
  reason text reaches the model.
- No existing hook's behavior regresses: all 13 current hook tests still pass, real output pasted.

## Notes

Do not wire events speculatively. Three events with a reason beat ten wired because they exist.

`PermissionRequest` auto-allow is the one item here with real blast radius: a too-broad allowlist
silently removes a confirmation the dev relies on. Start smaller than feels useful.
