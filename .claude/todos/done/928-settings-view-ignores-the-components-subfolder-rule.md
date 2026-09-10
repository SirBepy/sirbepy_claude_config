<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=6, reconfirm-count=1, content-hash=d8e9998a -->
<!-- duplicate-checked -->
<!-- Not a duplicate of done/334: that one narrowed tauri.md's 300-LINE rule to exclude colocated
     Rust test modules. This is the separate SUB-COMPONENT FOLDER rule in the same doc. -->
# tauri.md's sub-components-under-components/ rule is obeyed by no project

**Type:** task
**Origin:** ai

## Goal

Settle the divergence between `~/.claude/code-style/tauri.md`'s stated view layout and what real
Tauri projects do - by amending the doc, or by moving the files in the project that surfaced it.

## Context

Found 2026-09-02 by `/code-check` in `windows_taskbar_widgets` over `691e30f..5558dd9`. Relocated
here on 2026-09-05 by `/auto-do-todos` because its recommended fix edits a file in this repo.

`~/.claude/code-style/tauri.md:129`, "Frontend view pattern", says:

> "**Sub-components in the same folder.** If a view's `.ts` passes ~300 lines, extract pieces into
> `src/views/<view>/components/<piece>/`."

No sub-component in `windows_taskbar_widgets` does that. `src/views/settings/` is flat:
`widget-strip-field.ts`, `widget-strip-config.ts`, `widget-strip-drag.ts`, `widget-strip-dnd.ts`,
`widget-strip-lanes.ts`, `autostart-field.ts`, `lazy-ipc-field.ts`, `taskbar-monitor-field.ts`,
`schema.ts`, `settings.ts`.

`widget-strip-lanes.ts` (commit `3c47ea6`) is the newest and follows the same flat shape
deliberately: matching five existing siblings beat matching a doc none of them match.

So this is not a defect any commit introduced - it is a pre-existing, repo-wide divergence. Filed
because a written rule that nothing obeys is worse than either outcome: it makes every future
extraction re-litigate the same question.

The flat naming is not arbitrary - the `widget-strip-*` prefix already groups the five files that
belong together, which is most of what a subfolder would buy.

## Approach

Pick one, do not split the difference:

1. **Amend the doc** (cheaper, and matches reality): change tauri.md's rule to what real projects
   do - a shared filename prefix per feature group, flat inside the view folder. Keep it to one or
   two sentences; do not restructure the doc, same treatment `done/334` got.
2. **Move the files** in `windows_taskbar_widgets`:
   `src/views/settings/components/widget-strip/*.ts` for the five `widget-strip-*` files, updating
   imports. Bigger diff, touches `settings.ts`'s imports, and buys little given the prefix already
   groups them. This half is not executable from this repo's session.

Recommended: option 1. The doc describes a convention that codebase considered and did not adopt,
and the prefix grouping is legible.

Before amending, check whether any OTHER Tauri project on this machine does follow the
`components/<piece>/` shape - if one does, the rule is not universally dead and the wording should
narrow rather than invert.

## Acceptance

- Either tauri.md's rule matches what projects do, or the surfacing project matches the rule. Not
  neither.

## Notes

- **Q parked 2026-09-05 (amend tauri.md's sub-component rule, move the files in `windows_taskbar_widgets`, or delete the rule) - dev delegated to autopilot on 2026-09-10** via /loop-todos Phase 0. Autopilot takes the recommendation: amend the doc. The file-move half is not executable from this repo, and the `widget-strip-*` prefix already provides the grouping a subfolder would buy. The pre-amend check this todo asks for, whether any other Tauri project on this machine follows `components/<piece>/`, still runs before the wording changes.

- `/code-check` classed this **3 - judgment** and filed it: a convention decision with a real fork,
  repo-wide rather than diff-local.
- That review ran with `isolation: NOT held` (in-session, no reviewing subagent), so treat its
  judgement calls with more suspicion than usual.
- Relocated from `72` in `windows_taskbar_widgets` via /cleanup-todos 2026-09-05: the recommended
  fix edits `~/.claude/code-style/tauri.md`, which per root CLAUDE.md belongs in this repo's own
  backlog.
- DONE 2026-09-10 via /loop-todos cycle 1, resolved by amending the doc, which is the option delegated to autopilot on your behalf earlier the same day. The pre-amend survey this todo insisted on changed the answer: five Tauri repos were read (claude_usage_in_taskbar, pomodoro-overlay, server_supervisor, video_editor, windows_taskbar_widgets) and video_editor DOES use the components/piece shape at src/views/editor/components/timeline/. So the rule was not dead, it was minority, and code-style/tauri.md:129 was narrowed rather than inverted: extract into a flat subfolder named for the concern, or sibling files sharing a name prefix, and skip the components/ wrapper layer that only one of five repos uses. windows_taskbar_widgets keeps its flat widget-strip-* files and is now consistent with the doc, so the file-move half stays correctly unbuilt. python ci/run_all.py exits 0.
