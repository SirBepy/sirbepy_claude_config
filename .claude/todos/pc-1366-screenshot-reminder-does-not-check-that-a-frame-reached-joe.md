<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: done/pc-0821, pc-0825, pc-0487 and pc-0875 fixed other gaps of the same hook (later edits, peer files, old dirt, repo scoping); none covers "was the frame shown to Joe" -->
# The screenshot reminder hook passes when a test harness wrote PNGs that Joe never saw

**Type:** skill-improvement
**Origin:** ai
**Summary:** After a visual change, the turn-end reminder fires unless a screenshot was actually put in front of Joe, not merely written to disk.

## Goal

`hooks/ui-screenshot-reminder.py` stays quiet only when a frame tied to the visual change reached Joe in this chat (a `show_preview` call, a `SendUserFile` call, `/preview`'s image branch, or a Read of the image that the chat surfaces inline). A PNG that an e2e or view-harness run wrote does not count.

## Context

- The deleted `/close` skill carried this check in its Phase 0 as the "shown-to-Joe flag", kept separate from the "zero-writes flag" on purpose. Its text (now only in git: `git show b62c6c8^:skills/close/phase0-checks.md`) records the incident: a session that ran `pnpm run test:view` had 29 harness-written PNGs, the screenshot count read as non-zero, and Joe saw none of them.
- `/close` was deleted on 2026-11-12 (todo pc-1365). The question card Joe answered said the Stop hook "already reminds", which is true only in the weaker form: the hook compares the newest `.png` mtime under `.for_bepy/screenshots/` with the newest UI edit (read on 2026-11-12 by the builder that reworded `skills/e2e/SKILL.md`; that file's "Showing a captured frame to Joe" note now says so). So harness output silences it.
- `CLAUDE.md`'s "UI & visual changes" section still requires showing Joe; nothing enforces it.
- UNVERIFIED: which tool calls a Conductor chat uses today to put an image in front of Joe. Check `skills/preview/SKILL.md` and the Conductor MCP tool list (`show_preview`, a Read of an image) before choosing what the hook looks for.

## Approach

1. Read `hooks/ui-screenshot-reminder.py` and its tests in full, plus the four done todos named in the header, so the earlier fixes are not undone.
2. Add a transcript check for the current turn range: a tool call that shows an image to Joe, naming a file under this session's own `.for_bepy/screenshots/<id>/` folder or pushing a preview. The hook already reads the transcript for its turn boundary (see done/pc-0873).
3. Keep the mtime check as the cheap first gate: no fresh PNG at all still reminds.
4. Tests: harness PNGs with no show call still remind; a show call after the last UI edit stays quiet; a show call before a later UI edit reminds.

## Acceptance

- A turn that edits a `.css` file, runs a harness that writes PNGs, and shows nothing gets the reminder.
- A turn that shows a fresh frame does not.
- `python ci/run_hook_tests.py` is green and the hook still finishes inside its Stop timeout.
