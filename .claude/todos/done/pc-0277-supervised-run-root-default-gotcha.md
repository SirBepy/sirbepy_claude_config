<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=c51fce8f -->
# supervised-run: warn when -Project doesn't match -Root's cwd default

**Type:** skill-improvement
**Origin:** ai

## Goal

Prevent a repeated mistake: calling `sv.ps1 ensure -Project <other-repo>` from a session whose
shell cwd is a *different* repo silently launches the command in the wrong repo, because `-Root`
defaults to `(Get-Location).Path` (`sv.ps1:52`) rather than being derived from `-Project`.

## Context

2026-08-11, zng-admin session: needed to verify zng-biller's Flutter build alongside zng-admin's.
Called `sv.ps1 ensure -Project zng-biller -Cmd "flutter run ..."` without `-Root`, from a shell
whose cwd was still zng-admin's folder (the session's primary working directory). The supervisor
launched a *second zng-admin* flutter-run instance (`zng-admin:flutter-run-4`) instead of
zng-biller â€” the `-Project` label didn't override the actual root path used to run the command.
Caught only by noticing `sv.ps1 ls` showed two `zng-admin:` entries and zero `zng-biller:` ones;
had to `stop`/`rm` the errant entry and relaunch with an explicit `-Root
"C:\Users\tecno\Desktop\Projects\zng-biller"`.

Relevant code: `C:\Users\tecno\.claude\skills\supervised-run\sv.ps1:52` (`-Root` param default),
`:137` (`Resolve-Path $Root`), `:171` (`root = (Resolve-Path $Root).Path` sent to `/run`).

## Approach

In `C:\Users\tecno\.claude\skills\supervised-run\SKILL.md` step 1, add an explicit callout: when
the target repo differs from the current shell's cwd (e.g. verifying a sibling project from
another project's session), always pass `-Root "<absolute-path>"` explicitly â€” never rely on the
cwd default. Optionally, harden `sv.ps1` itself: if `-Project` is given and a `projects.json`
entry already maps that project name to a *different* root than the resolved `-Root`, warn/prompt
instead of silently creating a mismatched entry.

## Acceptance

- SKILL.md documents the gotcha with a concrete example (cross-repo launch from another project's
  session).
- (Stretch) `sv.ps1 ensure` detects a project-name/root mismatch against `projects.json` and
  errors instead of silently running in the wrong directory.

## Notes

- Migrated on 2026-08-12 from the dead top-level `~/.claude/todos/` path (was #01 there). That location was superseded by the repo-relative backlog on 2026-08-11; nothing reads it, so these were invisible to the Conductor app.
- completed, commit d31c4de
