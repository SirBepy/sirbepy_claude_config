<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done pc-0972 and pc-1290 pushed /brainstorm toward building without stopping; this is the opposite case, where the dev's own words ask to keep thinking -->
# /brainstorm's full-auto path should not build when the dev asked to keep thinking

**Type:** skill-improvement
**Origin:** ai
**Summary:** When the dev says to keep brainstorming or to be grilled, /brainstorm in a full-auto repo should keep talking instead of announcing a build.

## Goal

In a repo importing `full-auto.md`, a dev message that asks to think further stops the skill's "proceed without asking" branch from heading to implementation.

## Context

2026-11-04, `claude_usage_in_taskbar`, session 3f237cc5. Joe's opening message: "wed have to think about it more /brainstorm it more and in general grill me about it". Following step 7's full-auto branch and step 6's "file the todo AND build", Claude told him "Once you answer, Claude files the todo and builds it". He replied: "pls dont actually do this... i want us to mostly /brainstorm it and rly think it thru".

Steps 6 and 7 in `~/.claude-personal/skills/brainstorm/SKILL.md` only name go-words. They have no stop-words, so a request to keep thinking reads the same as silence. Done todos pc-0972 and pc-1290 both pushed toward building, for good reasons, and should stay.

## Approach

In `skills/brainstorm/SKILL.md`, add a stop-word list beside step 6's go-words: "brainstorm it more", "grill me", "think about it more", "don't build yet", "just the spec". When one matches the dev's own words, skip the full-auto proceed and the "file the todo AND build" line, and keep brainstorming until he names a next step. Worth asking at the end of such a talk what comes next, with writing a spec and stopping as an option, since that is what Joe picked here.

## Acceptance

- A full-auto repo plus "grill me about it" produces questions and no announcement of a build.
- A full-auto repo with no stop-word still proceeds as it does today.
