<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/14 (PR-preview-vs-no-text decision) and done/502 (commit/CLAUDE.md asking-mid-task contradictions) are archived and about different subjects than this one (ask_user_question's preview field rendering fake markup) -->
# Harden enforcement of the ask_user_question preview-must-be-real-markup rule

**Type:** skill-improvement
**Origin:** ai

## Goal

The rule "an `ask_user_question` option `preview` must be built from the app's real render
markup, never a hand-styled `<div style="...">` imitation" is documented in memory
(`feedback_question_previews_reuse_app_styles.md`, project
`c--Users-tecno-Desktop-Projects-claude-usage-in-taskbar`) but keeps getting violated anyway.
Find a way to catch this mechanically (a lint/hook on the tool call, or a stronger prompt-level
nudge) instead of relying on memory alone, which has now failed three times.

## Context

`feedback_question_previews_reuse_app_styles.md`'s own body already documents the pattern:
- 2026-10-18: machine-glyph/chat-row revamp - 3 rounds of hand-drawn previews before switching to
  real markup.
- 2026-10-20 (auto-update startup question): hand-drawn AND invented a layout the real component
  doesn't have.
- 2026-10-20, same day, LATER in the session (claude_usage_in_taskbar, "Wrap up when done"
  activation/visibility question): built four more hand-drawn `<div style="background:
  var(--color-surface)...">` fragments, despite the memory existing and being specifically about
  this exact tool. Joe: "these previews are so useless, i literally dont understand what im
  looking at, because again, youre not using the actual ui that we have in our app... pls note
  that AGAIN".

Each time, the rule was READ (it's in memory, in `/mockup`'s own SKILL.md step 3) but not
APPLIED under time pressure when building 3-4 option previews quickly for a single question. This
suggests memory-as-prose isn't sufficient here - the failure mode is "skipped under task
pressure", not "didn't know the rule existed".

## Approach

Ideas to evaluate, not prescriptive:
- A `PreToolUse` hook on the `ask_user_question`/`mcp__cc_conductor__ask_user_question` tool call
  (where available) that greps each option's `preview` field for `style="` / inline CSS
  properties and warns or blocks if found, nudging toward real markup instead.
- Strengthen the tool's own description (if editable) or the global prompt injection to state the
  rule closer to the point of the call, not just in a memory file that has to be recalled.
- A lighter escape hatch already exists in the memory file's own "repeated a third time" note:
  "if there's no time to do that before posting the question, it's better to skip the preview
  field/use plain option text than post another fake one" - consider whether the tool itself
  should make that trade-off easier (e.g. a documented "preview: omit" convention) rather than
  relying on the model remembering to reach for it under pressure.

## Acceptance

- A concrete mechanism exists (hook, lint, or prompt change) that would have caught at least one
  of the three documented incidents before the card was posted.
- Does not block/slow down a genuinely real-markup preview.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.

## Notes

This is a cross-project concern (the tool and the rule are global), filed here per CLAUDE.md's
"work on `~/.claude` itself... always lands in `.claude/todos/`, never in the surfacing project's
session" rule, even though all three incidents were observed in `claude_usage_in_taskbar` sessions.
