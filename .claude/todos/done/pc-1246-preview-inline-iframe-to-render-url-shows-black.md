<!-- Claim before executing: .claude/todos/.claims/ per skills/close/ai-todos-format.md -->
<!-- duplicate-checked: 1174 (done) added the inline-iframe step and saw it work once on a gallery; this is a case where the same step showed a black box. The other hits are clockify and create-pr cards. -->
# /preview's inline iframe card showed Joe a black box for a full demo page

**Type:** skill-improvement
**Origin:** ai
**Summary:** When /preview shows a pushed page inline before a question, the chat card reliably shows the page, or the skill says when it does not work.

## Why

Joe saw a black box on 2026-10-25 ("i just see black") and a plain white card on 2026-10-28; the printed render-url returned 404 while the check URL returned 200.

## Goal

When `/preview` tells Claude to show a pushed page inline before a question, the chat card reliably shows the page,
or the skill says when that step does not work and what to do instead.

## Context

- `skills/preview/SKILL.md`, Before/after branch, last bullet: "Send a `show_preview` card whose HTML is an iframe
  to that `render-url` immediately before the question". Added by todo 1174, whose notes say the inline card was
  seen working once (zng-biller gallery, 2026-10-13) and was not re-verified live when the step was written down.
- 2026-10-25, dashboard-a session ac3d112b: `build_gallery.py docs/design/demo.html --slug dashboard-a-demo-loop
  --check --post` returned HTTP 200 and a `render-url`. A `show_preview` card whose HTML was only
  `<body style="margin:0;background:#0A0A0B"><iframe src="<render-url>" style="border:0;width:100%;height:900px">`
  showed Joe a black box ("i just see black"). The preview-panel entry itself was fine.
- UNVERIFIED cause, would check by reproducing: the card's sandbox blocking the localhost frame (the `show_preview`
  description says it "renders in a sandboxed frame with no access to the app"), the page being a large script-driven
  app rather than a static gallery, or the card's own dark background plus a page that had not painted yet.
- Same session: `ask_user_question` option previews with `<img src="file:///...png">` did render screenshots.
- Likely cause, measured 2026-10-28 (joes_tabs_ut session 594e623b, static before/after manifest gallery, slug
  `ut-restyle-shots`, a re-push of an existing slug): the `render-url:` that `build_gallery.py --post` prints is the
  POST response's entry id (`c1e4bf58-...`), and `curl` on `/hooks/preview-render/<that id>` returned **404, 0 bytes**,
  both right after the first push and after a re-push. The `check OK:` URL printed by `--check` in the same run
  (`c308844b-...`) returned **200, 765599 bytes**. Joe saw the iframe card as plain white. So the inline step is fed a
  URL that serves nothing; fix the printed `render-url` (or have SKILL.md use the `--check` URL / curl the URL first).
- Recurred 2026-11-04 (zng-admin session c148d3b9, slug `sc-56607-design-pass`, 1.3 MB manifest gallery): `--post` returned
  200 and `render-url .../49751c8b-...`, `curl` on it returned 404, and `show_preview` refused the iframe card with HTTP 410
  both times, including right after a re-post, because the id does not change on a re-post. So the 410 error's advice
  ("Re-run the gallery --post for a fresh render-url") cannot work here. The `--check` URL (`6ea39f2d-...`) was not tried in a
  card. Joe did see the gallery in the preview panel. Workaround used: `Read` an ffmpeg side-by-side PNG into the chat.

## Approach

1. Reproduce with two pages: a small static gallery (the 1174 case) and a large scripted page (for example
   `dashboard-a/docs/design/demo.html`), each via `build_gallery.py --post` then a `show_preview` iframe card. Note
   which one renders.
2. Rewrite the bullet to match: keep the iframe where it works, and for the failing kind tell Joe by name which
   preview-panel entry to open, using `file:///` screenshots in the question card's option previews for the
   comparison itself.

## Acceptance

The SKILL.md step names when the inline iframe works and what to do when it does not, verified once by a real render
of each kind.

## Notes

- Removed the render-url print and render_url_from_response from build_gallery.py, replaced the SKILL.md iframe step with 'pass the page as the card's own html'; test_build_gallery.py now asserts no render-url line.

## Update 2026-11-06: drop the iframe step instead

Joe saw another blank card (`cv-top3-layouts-inline`, claude_usage_in_taskbar): html was only an iframe to a render id
that the daemon no longer held after a restart (404 when curled). A card replays from the transcript, so the stub
outlives its page. claude_usage_in_taskbar now refuses (HTTP 422) any chat-card push that iframes
`/hooks/preview-render/`, held or not, and its `show_preview` description says to put the page's html in `html`.
So the resolution is to remove the "inline iframe to render-url" step from `skills/preview/SKILL.md` (~lines 105-111)
and the `render-url:` print in `build_gallery.py`, and tell Claude to pass the gallery html as the card's own `html`
(or rely on the panel push), rather than the reproduce-and-document plan above. Keep `--check`'s own use of the render
endpoint, which never reaches a card. Update `test_build_gallery.py` and run the two `ci/` checks.
