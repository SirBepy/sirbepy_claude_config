<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for ui-screenshot-reminder / screenshot hook: no hit. -->
# ui-screenshot-reminder blocks read-only turns in a shared checkout

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the `ui-screenshot-reminder` stop hook fire on UI files THIS session actually edited, not on
every dirty UI file in the working tree.

## Context

2026-08-27, zng-app. A turn that made zero edits - it read one Dart widget and measured two PNGs
attached to the prompt - was blocked on stop with:

> [ui-screenshot-reminder] This turn touched UI-ish files. Per CLAUDE.md's "UI & visual changes"
> rule: bring the app up via /supervised-run ... capture a screenshot

Nothing had been written yet, so there was nothing to screenshot. The turn was a measurement pass
that ENDED in a question to the dev, and the hook forced a turn spent explaining why the demand did
not apply.

Likely cause: the hook decides "touched" from `git status` dirty paths rather than from this turn's
own Edit/Write tool calls. zng-app is a shared checkout routinely running 5+ concurrent Conductor
sessions, and at that moment four UI files were dirty from OTHER sessions
(`request_v2_contact_fields.dart`, `request_v2_identity_fields.dart`, `v2_create_account_screen.dart`,
`v2_verify_screen.dart`). UNVERIFIED - the hook source was not read from the project session, per the
global rule against doing `~/.claude` work from inside a project. Confirm before fixing.

The rule the hook enforces is right and should stay; a real visual change does need showing. This is
about which turns it classifies as visual changes.

## Approach

1. Read the hook (locate it under `C:\Users\tecno\.claude\hooks\`) and confirm how it decides a turn
   touched UI files. If it reads `git status`, that is the bug.
2. Gate on this turn's own `Edit`/`Write`/`NotebookEdit` tool calls against UI paths instead. A turn
   with no write tool call against a UI file can never owe a screenshot.
3. If the transcript-inspection needed for step 2 is not available to the hook, fall back to
   comparing dirty paths against files modified since the turn started, which still excludes a
   peer's long-standing dirty file.
4. Add a test case: a turn that only READS a `.dart`/`.css` file is not flagged.

## Acceptance

- A read-only turn touching UI files is not blocked.
- A turn that actually edits a UI file and captures no screenshot IS still blocked.
- Peer sessions' dirty UI files never trigger this session's hook.
- `python ci/run_all.py` passes.

## Notes

Filed from a project session per global `CLAUDE.md`: spotting and filing global findings is allowed,
editing the global tree from a project session is not. Do not fix this from zng-app.
- Duplicate of 487 - merged during /cleanup-todos 2026-08-29. Same defect: ui-screenshot-reminder.py's changed_files() computes 'touched' from the whole working tree (git diff HEAD plus git ls-files --others) instead of this turn's own edits. 487 already carried the 2026-08-26/27 zng-app recurrences; this file's turn-start-snapshot fallback and its read-only-turn and peer-dirty-file acceptance bullets were folded into 487 first.
