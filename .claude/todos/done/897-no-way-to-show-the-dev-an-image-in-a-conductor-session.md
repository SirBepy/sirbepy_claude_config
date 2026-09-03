<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/preview` takes HTML but not images, so a screenshot cannot reach Joe in a Conductor session

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/preview` a first-class way to push one or more image files into Conductor's preview panel,
so "show Joe the screenshot" stops needing a hand-rolled base64 payload every time.

## Context

Found 2026-09-02 during a long hubbub session that captured ~14 screenshots.

**In a Conductor-hosted session, Claude's own assistant text is not rendered in the chat at all** -
only `mcp__cc_conductor__send_message` bubbles are. Reading a PNG back with the `Read` tool puts it
in Claude's context but Joe never sees it. And in that session **no `SendUserFile` tool existed**,
even though root `CLAUDE.md`'s "UI & visual changes" rule instructs Claude to "capture a screenshot
via SendUserFile", and the global `ui-screenshot-reminder` stop-hook fires that same instruction.

So the documented path is unreachable and the hook demands something impossible. The gap was worked
around three times in one session by hand-building an HTML page with base64 `data:` URIs and POSTing
it to `http://127.0.0.1:27182/hooks/preview`, which works and stayed under the ~2 MB cap at about
1.0 MB for two full-resolution 1920x1080 PNGs.

`/preview`'s SKILL.md already documents that endpoint and even says "**Images are never inlined**"
for its markdown branch, citing that same 2 MB cap - so the omission is deliberate for markdown, but
it leaves no supported path for the plain "look at these screenshots" case.

## Approach

1. Add an image branch to `~/.claude/skills/preview/SKILL.md`: given one or more image paths (or a
   directory), render a minimal HTML page with each inlined as a `data:` URI plus its filename as a
   caption, then push it through the existing POST exactly as the markdown branch does.
2. Downscale or refuse past the ~2 MB body cap rather than letting the POST 413. Two 1920x1080 PNGs
   fit; a dozen will not, so cap by cumulative encoded size and say what was dropped.
3. Reuse the slug convention so re-pushing the same set refreshes in place.
4. Then reconcile the instructions that currently point at a tool that may not exist: root
   `CLAUDE.md`'s "UI & visual changes" bullet and the `ui-screenshot-reminder` stop-hook should name
   `SendUserFile` **or** `/preview`'s image branch, whichever the session actually has.

## Acceptance

- `/preview shot1.png shot2.png` puts both in the Conductor panel with no hand-written Node.
- A set over the cap fails with a clear message naming what was dropped, never a raw 413.
- `CLAUDE.md` and the stop-hook no longer instruct a session to use a tool it may not have.

## Notes

- Verified working payload shape that session: `{ title, slug, html, source: "terminal",
  session_id: process.env.CLAUDE_CODE_SESSION_ID }` POSTed to `/hooks/preview`; omitting
  `session_id` means the push never appears in any chat.
- Filed from a hubbub session per CLAUDE.md's rule that findings about the global tree belong in
  this repo's own backlog, not the surfacing project's.
- Completed in /mega-todos wave 1, commit e71a91a: /preview gained an image branch inlining images as data URIs, and CLAUDE.md plus ui-screenshot-reminder.py now point at a tool the session actually has. CLAUDE.md stayed under its token ceiling.
