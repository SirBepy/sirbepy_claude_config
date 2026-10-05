<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=4, reconfirm-count=1, content-hash=e6a15bbf -->
<!-- duplicate-checked: grepped this backlog for "tauri.md", "view files only", "300-line" and "size rule" on 2026-09-22 - no hits. -->
# `code-style/tauri.md`'s ~300-line rule says "views only", but practice splits shared modules and CSS too

**Type:** skill-improvement
**Origin:** ai

## Goal

`code-style/tauri.md` states the size convention the way it is actually applied, so a reviewer
stops having to guess whether the letter or the practice governs.

## Context

Surfaced 2026-09-22 from a `claude_usage_in_taskbar` session's `/close` code review, as an
"unwritten-rule observation" (a doc gap, not a code defect). Filed here because the fix is a change
to this repo's global code-style doc, per `CLAUDE.md`'s rule that a todo belongs in the backlog of
the repo it changes. The project session did not edit this file.

**What the doc says**, `code-style/tauri.md` line 129 (read 2026-09-22): *"If a view's `.ts` passes
~300 lines, extract pieces into a flat subfolder... This threshold is for view files only; a non-view
support module such as `state.ts` may sit past ~300 lines unsplit, as it does in
`server_supervisor`."* The doc also says nothing at all about a size rule for CSS files.

**What practice does, in `claude_usage_in_taskbar` alone**, all non-view modules split repeatedly for
size under that same ~300 number:

- `src/shared/chat/held-messages.ts` - split 3 times (done/543, done/637, done/556), now 560 lines and
  filed a 4th time (that repo's todo 935).
- `src/shared/chat/event-store.ts`, `composer.ts`, `chat-event-handler.ts` - each split 3-5 times;
  `chat-event-handler.ts` is still open for size (that repo's todo 912).
- CSS files split for size too: `session-statusbar.css` (that repo's todo 892, `19f79ba5`) and
  `model-effort-modal.css` (that repo's todo 936).

So the doc's own exemption is not honoured, and it is silent on CSS where practice is not. A reviewer
reading the letter would decline every one of those splits; a reviewer following practice files them.
Both happened in the same review session, which is the cost.

## Approach

Decide which one is right, then make the doc say it. Do not just delete the exemption without a
reason, since `server_supervisor`'s unsplit `state.ts` was cited as a deliberate counter-example.

1. Likely resolution: the size rule applies to any module that accretes independent concerns
   (views AND shared modules like `src/shared/chat/*`), while a genuinely single-concern module
   (a state container like `state.ts`) may exceed it. That keeps the counter-example valid and
   matches practice. State it as a concern test, not a folder test.
2. Add one sentence on CSS: whether a per-feature `.css` file falls under the same threshold, given
   that two have already been split for it.
3. Keep the change to the rule text. Do not restate the incidents above in the doc, per this repo's
   own rule that design rationale belongs in the commit message, not the file.

## Acceptance

- `code-style/tauri.md`'s size rule describes which modules it covers in a way that matches how it is
  applied, and says something about CSS files.
- `python ci/run_all.py` passes after the edit.

## Notes

- Dropped via /cleanup-todos 2026-10-05: worth 4/10, a one-sentence style-guide drift note with no recurring cost.
