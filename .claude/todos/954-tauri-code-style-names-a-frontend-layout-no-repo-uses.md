<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=7, reconfirm-count=1, content-hash=8a15e740 -->
<!-- duplicate-checked: grepped this backlog and done/ for "tauri.md", "code-style", "components/" and "view extraction" - no existing todo covers the frontend-extraction layout rule in code-style/tauri.md. -->
# code-style/tauri.md names a frontend extraction layout no repo actually uses

**Type:** task
**Origin:** ai

## Goal

Make `~/.claude/code-style/tauri.md`'s frontend view-extraction rule describe what Tauri projects
here really do, so agents stop having to be told which of the two shapes to follow.

## Context

Surfaced 2026-09-05 in the `server_supervisor` repo during an auto-do-todos run, by two separate
subagents independently, which is why it is worth a file rather than a shrug.

`~/.claude/code-style/tauri.md` (around line 129, Frontend view pattern) says:

> If a view's `.ts` passes ~300 lines, extract pieces into `src/views/<view>/components/<piece>/`.

`C:\Users\tecno\Desktop\Projects\server_supervisor` has never done that. Verified on 2026-09-05 with
`find src/views/dashboard -type d -iname "components"`, which returns nothing. What
`src/views/dashboard/` actually contains is flat sibling files (`add-project.ts`, `combobox.ts`,
`helpers.ts`, `home-screen.ts`, `modal-fields.ts`, `modals.ts`, `preset-modals.ts`,
`project-screen.ts`, `state.ts`, `stats-strip.ts`) plus exactly one flat topic subfolder, `menus/`,
holding `cmd-menu.ts`, `project-menu.ts` and `group-menu.ts`. No `components/<piece>/` anywhere.

The cost is concrete rather than cosmetic. A cleanup scout hit the mismatch and flagged it; a
builder dispatched to split `project-screen.ts` had to be told in its prompt to follow the repo over
the doc, and without that line it would plausibly have introduced a third layout into a directory
that already has two. The extraction shipped as a flat sibling, `src/views/dashboard/proxy-hub.ts`
(commit `0bbaaec` in that repo).

The Rust half of the same file is fine and is not in question: its sibling-`.rs`-plus-folder rule
has been followed eight times in that repo and matches reality exactly. This is only about the
frontend view-extraction line.

## Approach

Check more than one repo before rewriting, since a rule that matches zero repos and a rule that
matches one out of three are different problems. Look at whatever other Tauri frontends exist
locally, `claude_usage_in_taskbar` being the obvious second, and see which shape they use.

Then pick one and write it down:

- If flat siblings are the real convention everywhere, replace the `components/<piece>/` line with
  the flat-sibling shape, and mention the flat topic subfolder (`menus/`) as the escalation once one
  concern grows past a single file. That is what `server_supervisor` actually converged on
  unprompted, twice.
- If the two repos genuinely disagree, say so in the doc and give the tiebreak rule rather than
  asserting one shape, so an agent stops having to guess.

Whichever way it lands, keep the ~300-line trigger itself. Nothing about the threshold is in
dispute, only the destination layout.

Also worth deciding while in there: the same rule is written for view files specifically, so a
shared non-view support module such as `state.ts` has no written guidance at all. The same
`/code-check` pass noted `state.ts` sitting at 324 lines with no rule that covers it. Either extend
the rule to non-view modules or state deliberately that it does not apply to them.

## Acceptance

- `~/.claude/code-style/tauri.md`'s frontend extraction rule matches what a real Tauri repo on this
  machine does, with the checked repos named in the file or the commit message.
- A fresh agent reading only the doc would produce the same layout the repo already uses, with no
  correction needed in its dispatch prompt.
- The Rust module rules in the same file are left alone.

## Notes

Filed 2026-09-05 from a `server_supervisor` session, into this repo's backlog rather than that
project's, per the root `CLAUDE.md` rule that findings about the global `~/.claude` tree belong
here. No edit to `~/.claude` was made from that session.
