<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- 426/427/444/446 all name this hook, but only as an example of Stop-hook plumbing or as doctrine overlap. None touch its file-selection. -->
# `ui-screenshot-reminder` fires on repo dirt the turn never touched

**Type:** task
**Origin:** ai

## Goal

The hook decides "this turn touched UI-ish files" from the **whole working
tree's** dirty + untracked set, not from what the turn actually changed. Any
pre-existing uncommitted UI file makes it fire on every unrelated turn until
someone commits.

## Observed 2026-08-22

A `revaire-mobile` session whose only write was one markdown todo file got the
reminder. Reconstructed from the hook's own code, not guessed:

- `changed_files()` (`hooks/ui-screenshot-reminder.py:81-86`) runs
  `git diff --name-only HEAD` + `git ls-files --others --exclude-standard`.
  Both report the tree's state, with no relation to the turn.
- The session's Bash cwd had drifted to `claude_usage_in_taskbar`, where two
  files were **already** dirty from earlier work:
  `src/views/sessions/sessions-mobile.css` and `location-picker.ts`. The `.css`
  matches `UI_EXTENSIONS` (`:34`).
- So the reminder was correct on its own terms and wrong about the turn. Acting
  on it would have meant launching Joe's daily-driver taskbar app to screenshot
  a change nobody made, which a separate rule forbids anyway.

Two distinct defects, worth separating:

1. **Attribution.** Tree state is the wrong input. The turn's own edits are.
2. **cwd drift.** `payload["cwd"]` follows the shell, so a session working in
   repo A can be judged against repo B.

## Approach

- Prefer the turn's real edits over `git`: the Stop payload's transcript, or a
  `PostToolUse` sidecar that records Edit/Write paths into the session marker
  file the hook already maintains (`:48-49`), then reads them at Stop.
- If git stays the source, at minimum diff against a snapshot taken at
  `SessionStart` so pre-existing dirt is subtracted.
- Pin the repo to the session's primary working directory rather than whatever
  cwd the last shell command left behind.
- Extend `hooks/test_ui_screenshot_reminder.py` with the two regressions.

## Acceptance

- [ ] A turn that edits only `.md` does not fire, even with a dirty `.css` in the tree
- [ ] A turn that edits a `.tsx`/`.css` still fires
- [ ] A turn in repo A is judged against repo A after the shell has cd'd to repo B
- [ ] Existing tests in `hooks/test_ui_screenshot_reminder.py` stay green

## Notes

- Cheap-fix option if the above is too invasive: keep the tree scan but require
  the matched file to also appear in the turn's edits.
- Filed from a `revaire-mobile` session. Per global CLAUDE.md, filing here is
  allowed; the hook itself must not be edited from a project session.
