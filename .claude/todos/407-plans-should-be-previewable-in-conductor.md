<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=2, content-hash=f4d21b82 -->
# Plans should be readable in Conductor's preview panel, not only as files on disk

**Type:** skill-improvement
**Origin:** dev

## Goal

Make a written plan something Joe can read **in the app**, the way a mockup already is, instead of
having to open a markdown file in an editor.

## Context

Joe, 2026-08-19, during the zng-app share-to-claim work: *"i want to be able to preview plans in
this app, lets make note of that"*.

The trigger: a session produced `PLAN-three-flows.md` plus seven spec files, ~2,300 lines total,
all as markdown on disk. Reviewing them meant leaving the app. He asked for a rendered reader
instead, and one was hand-built for that session as a one-off. The one-off works but nothing makes
it repeatable.

What already exists and is close:

- `~/.claude/skills/preview/SKILL.md` pushes **static HTML** into Conductor's preview panel via
  `POST http://127.0.0.1:27182/hooks/preview`, with slug-based iterate-in-place. It takes HTML, not
  markdown, so today every caller has to render markdown itself.
- Python `markdown` 3.10.2 is installed and available, so rendering is not the hard part.
- The gap is purely that there's no standard "render these markdown files into one navigable page
  and push it" path, so each session reinvents the styling and the nav.

## Approach

Smallest thing that works, and it should stay small:

1. Add a markdown branch to `/preview`: given one or more `.md` paths (or a directory), render them
   into a single self-contained HTML page with a document sidebar, then push it exactly as the HTML
   branch does today. Same slug convention, so re-running after editing a plan refreshes in place.
2. Keep the styling in one place inside the skill rather than per-session, so plans look consistent
   and Joe learns one layout.
3. Do not build a server, a watcher, or a framework. The existing hook endpoint plus a static page
   is the whole mechanism.

Reference implementation to lift from, written for the share-to-claim session:
`zng-app/.for_bepy/share-to-claim/build_reader.py`. It handles the sidebar, anchor nav, tables and
code blocks, and was pushed successfully through the hook endpoint.

## Acceptance

- `/preview <some.md>` and `/preview <dir-of-md>` both render and push without the caller writing
  any HTML.
- Re-running on the same input refreshes the existing panel entry rather than appending a new one.
- A plan with tables, nested lists, code blocks and links renders correctly.
- The HTML branch keeps working exactly as it does now.

## Notes

- Size limit is real: the endpoint rejects above ~2MB. A directory of specs plus inlined images
  could exceed it, so the markdown branch should not inline images by default.
- Related: this is the same panel `/mockup` and the `<cc-preview:SLUG>` chat wrapper target.
