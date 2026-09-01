<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=2, content-hash=5d3a1982 -->
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

Recurred 2026-08-27 in `zng-app`: a **read-only** turn (Grep/cat only, zero Edit or Write
calls) drew the reminder, because the tree already carried another concurrent session's
dirty `lib/ui/loan_request_v2/*.dart` files. Same root cause, second repo.

## Approach

- Prefer the turn's real edits over `git`: the Stop payload's transcript, or a
  `PostToolUse` sidecar that records Edit/Write paths into the session marker
  file the hook already maintains (`:48-49`), then reads them at Stop.
- If git stays the source, at minimum diff against a snapshot taken at
  `SessionStart` so pre-existing dirt is subtracted. Comparing dirty paths against
  files modified since the TURN started is the weaker fallback, and still excludes
  a peer's long-standing dirty file (from 825).
- Pin the repo to the session's primary working directory rather than whatever
  cwd the last shell command left behind.
- Extend `hooks/test_ui_screenshot_reminder.py` with the two regressions.

## Acceptance

- [ ] A turn that edits only `.md` does not fire, even with a dirty `.css` in the tree
- [ ] A turn that edits a `.tsx`/`.css` still fires
- [ ] A turn in repo A is judged against repo A after the shell has cd'd to repo B
- [ ] A read-only turn (zero Edit/Write calls) is never blocked, however dirty the tree (from 825)
- [ ] A peer session's dirty UI file never triggers this session's hook (from 825)
- [ ] Existing tests in `hooks/test_ui_screenshot_reminder.py` stay green

## Notes

- Cheap-fix option if the above is too invasive: keep the tree scan but require
  the matched file to also appear in the turn's edits.
- Filed from a `revaire-mobile` session. Per global CLAUDE.md, filing here is
  allowed; the hook itself must not be edited from a project session.
- **Recurrence 2026-08-26, `zng-app`.** A session whose only output was chat
  messages (zero file writes, `git status` byte-identical at close to session
  start) fired the reminder twice, then blocked the Stop hook. The dirt was
  `lib/ui/loan_application/loan_search_biller_account_screen.dart`, already
  staged before the session began. Cost was three wasted turns and visible
  user frustration, since the only available response to a blocking hook is to
  argue with it. Second repo, second confirmation, and the blocking behaviour
  makes it worse than a noisy warning - raises priority.
- Done via /mega-todos 2026-09-01 (abda5b3): the reminder now fires only on files the turn actually changed, with a regression case for pre-existing dirt.
