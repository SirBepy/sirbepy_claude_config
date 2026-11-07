<!-- Claim before executing: .claude/todos/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard's hits (pc-0450, pc-1173, pc-1306, pc-0010, pc-0011) are by title a code-check timing rule, the push-gate mark, a Shortcut reader, a todo-archive script and an orphan-process audit; none concerns the preview skill's push -->
# /preview skill: a push script so a hand-written POST cannot omit session_id

**Type:** skill-improvement
**Origin:** ai
**Summary:** Add a small script to the preview skill that pushes an html file to Conductor with the chat's session id, so a hand-written POST cannot forget it.

## Goal

`skills/preview/` gets `push_html.py <file.html> --slug <s> --title <t> [--source chat|terminal]` that reads `CLAUDE_CODE_SESSION_ID`, POSTs to `http://127.0.0.1:27182/hooks/preview` and prints the returned id; `SKILL.md` points at it.

## Context

Found by the `/close` retrospective of the claude_usage_in_taskbar "subchat mockups" chat, 2026-11-05. `skills/preview/SKILL.md:116` already says `session_id` "is required, not optional" and that omitting it means the push "will never be visible in any chat's panel". Claude still hand-wrote the same inline Python POST about seven times for an iterated mockup board, and the first one left `session_id` out, so Joe saw the previous board for two rounds ("im still seeing this preview..."). The rule is written; nothing enforces it where a script is hand-rolled, and a repeated hand-rolled step is the signal for a script. `build_gallery.py:346` already reads the env var, so the pattern exists for galleries only.

## Approach

1. Write `skills/preview/push_html.py` (stdlib only, `urllib`), refusing with a plain error when `CLAUDE_CODE_SESSION_ID` is unset instead of posting without it.
2. Replace the node/PowerShell snippets at SKILL.md lines 123-130 with one call to it; keep the endpoint and body shape documented.
3. Note that a push under the slug already open in the panel replaces it in place and the panel follows it, while a new slug only dots the picker (observed in the panel's `onLivePush`, `src/views/sessions/preview-panel-selection.ts` in claude_usage_in_taskbar).

## Acceptance

- Running it with the env var unset exits non-zero without posting.
- Running it from a Conductor chat shows the page in that chat's panel.
- `python ci/check_skill_frontmatter.py` and `python ci/check_instruction_budget.py` pass.

## Notes

- Added skills/preview/push_html.py + test_push_html.py (exits 2 without posting when CLAUDE_CODE_SESSION_ID is unset); SKILL.md Steps now point at it. The 'shows in the chat panel' acceptance bullet is verify-only (needs a live Conductor chat).
