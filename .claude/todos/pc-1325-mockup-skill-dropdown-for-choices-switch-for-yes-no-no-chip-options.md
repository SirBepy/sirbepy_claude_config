<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog and done/ for "chip", "dropdown", "mockup skill"; pc-0415/0416/0438 (done) are about plan-step schema, render-gated CSS and scratch disposal, none about control types -->
# /mockup skill: dropdown for a choice, switch for yes/no, never chip rows as options

**Type:** task
**Origin:** dev
**Summary:** Add Joe's control rule to the `/mockup` skill's Staging section so every mockup Claude builds follows it.

## Why

Joe, 2026-11-05, claude_usage_in_taskbar brainstorm chat, after approving the shared-mockup board: "from now on, lets stop using chips as options or buttons or toggles, but rather lets use dropdowns... actually toggle switches can still be used too occasionally if its only a yes/no or 'on/off' option".

## Goal

`skills/mockup/SKILL.md` (Staging section, "Live simulator controls" bullet, which today only says "buttons/sliders") states: a choice between options is a dropdown (native `<select>`), a plain yes/no or on/off is a switch, and chip rows, pill rows or button groups are not used as options, buttons or toggles in a mockup.

## Context

- Scope as Joe said it is "mockups" he reviews; whether it also binds the app's own shipped UI was not asked. UNVERIFIED which shipped surfaces use chip rows as options; do NOT extend the rule to shipped UI without asking him.
- The board that carried the rule: `claude_usage_in_taskbar/.for_bepy/mockups/mockup-shared-mockup.ts` (gitignored, may be gone). Design spec: that repo's `.claude/todos/pc-1620-shared-mockup-one-page-many-subchats-each-with-its-own-controls.md`.
- Surfacing chat did not edit this global skill, per the rule against global edits from inside a project chat.

## Approach

1. Edit the "Live simulator controls" bullet in `skills/mockup/SKILL.md`.
2. Keep it one or two sentences; no new section.

## Acceptance

- The bullet states the rule; `python ci/check_skill_frontmatter.py` and `python ci/check_instruction_budget.py` still pass.
