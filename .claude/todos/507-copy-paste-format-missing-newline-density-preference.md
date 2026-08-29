<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=187bf40c -->
<!-- duplicate-checked -->
# copy-paste-format.md doesn't say Joe wants drafted messages broken into short lines, not dense paragraphs

**Type:** skill-improvement
**Origin:** dev

## Goal

Add a line to `~/.claude/refs/copy-paste-format.md`'s "Message length" section documenting that
Joe wants a drafted message (Slack/teammate copy, inside a blockquote) broken into short
paragraphs/lines rather than one dense block, separate from the existing sentence-count cap.

## Context

2026-08-24, zng-admin session 7743f94c-4c39-4339-866d-a8e54d350f8a: Claude drafted a Slack message
for Gohar as one dense paragraph inside a blockquote. Joe: "bad, i like new lines, and i HATE em
dashes." The em-dash half is already covered by the standing global rule (and now also by
todo 506, a hook regression that let it through) - but "i like new lines" names a formatting
preference `copy-paste-format.md` doesn't currently state anywhere. The file's "Message length"
section caps sentence/bullet count but says nothing about whether a drafted teammate message
should read as short line-broken clauses (what Joe asked for) vs a normal prose paragraph.

## Approach

Add a bullet to the "Message length" section (or a new short subsection) along these lines: for a
drafted message meant to be copy-pasted to a teammate, prefer short lines/short paragraphs
separated by blank lines over a single dense paragraph, even when the total length is already
within the 2-4 sentence cap. Keep it scoped to copyable teammate-message content specifically, not
Claude's own prose replies to Joe (those already follow the terse-replies snippet).

## Acceptance

- `copy-paste-format.md` states the line-break preference explicitly, so a future session drafting
  a teammate message doesn't need to be corrected live for it again.

## Notes

Filed from zng-admin (a project session) per CLAUDE.md's rule that global `~/.claude` findings go
in this repo's own backlog, never the surfacing project's. This session did not edit `~/.claude`
itself, only filed this todo.
