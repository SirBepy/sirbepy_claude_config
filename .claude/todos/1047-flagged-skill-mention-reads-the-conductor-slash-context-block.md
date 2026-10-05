<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=f6b0c74b -->
<!-- duplicate-checked: 491/332 cover peer/daemon envelopes, 342 covers first-line scope; this is the conductor-slash-context block appended to Joe's own prompt -->
# flagged-skill-mention fires on skill names inside Conductor's machine-generated slash-context block

**Type:** bug
**Origin:** ai

## Goal

`hooks/flagged-skill-mention.py` injects a flagged skill's SKILL.md only when Joe's own words mention
it. It should never fire on text inside the `<conductor-slash-context>` block that Conductor appends
to the prompt.

## Context

Session ed215154 (2026-09-29), revamping `/iterate-it`. Joe's prompt named `/iterate-it` and
`/brainstorm`. Conductor then appended a `<conductor-slash-context>` block quoting each skill's
description. iterate-it's description says "Also invoked as a bounded nested step by /autopilot and
/auto-do-todos". The hook matched those two names inside the quoted description, and injected
auto-do-todos' full SKILL.md (36.7KB) on the first prompt. On the second prompt it injected
autopilot's SKILL.md (14.1KB) because `/autopilot` again appeared only inside the slash-context
block. Joe never asked to run either skill. The injected text says "treat this as informational"
when the name is only quoted, so nothing ran, but about 50KB of context was spent for nothing.

Distinct from 491/332, which cover peer and daemon envelopes that start the prompt. Here the prompt
is Joe's own, and only a trailing machine-generated block carries the name.

## Approach

Strip every `<conductor-slash-context>...</conductor-slash-context>` span from the prompt before
matching. Add a test case that takes iterate-it's real description inside that block and asserts no
injection.

## Acceptance

- The hook's self-test gets a case where the flagged name appears only inside a
  `<conductor-slash-context>` block, and it asserts no injection.
- A flagged name typed by Joe outside the block still fires.
