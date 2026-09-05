<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
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

- `/code-check` classed this **3 - judgment** and filed it: a convention decision with a real fork,
  repo-wide rather than diff-local.
- That review ran with `isolation: NOT held` (in-session, no reviewing subagent), so treat its
  judgement calls with more suspicion than usual.
- Relocated from `72` in `windows_taskbar_widgets` via /cleanup-todos 2026-09-05: the recommended
  fix edits `~/.claude/code-style/tauri.md`, which per root CLAUDE.md belongs in this repo's own
  backlog.

## Open questions

Written by /auto-do-todos on 2026-09-05. The next run opens with these.

- [ ] [TOOLING] Amend tauri.md's sub-component rule to match reality, or move the files in
      `windows_taskbar_widgets` to match the doc? - options: amend the doc / move the files /
      leave both and delete the rule. Recommended: amend the doc, because the `widget-strip-*`
      prefix already does the grouping a subfolder would buy, and no project on this machine was
      found obeying the rule as written.
