<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=be7ad57f -->
<!-- duplicate-checked: hits 330/407/43/897 are done and cover stage width, plan previews, autopilot deletion and image previews; none covers cross-frame injection failing in the sandboxed panel -->
# /mockup: iframe-based live-variant boards silently break inside Conductor's preview panel

**Type:** skill-improvement
**Origin:** ai

## Goal
A `/mockup` board that frames the project's real pages and switches variants live keeps working when pushed into Conductor's preview panel, instead of rendering but ignoring every button.

## Context
2026-10-04, sirbepys-minecraft-server (static site) session. The board iframed the real pages (served on localhost) and injected variant CSS/DOM via `iframe.contentDocument`. Verified working in a plain Playwright tab, pushed to the panel as a wrapper `<iframe src="http://127.0.0.1:<port>/mockup.html">`. Joe: "im clicking the buttons but i dont see anything changing" and the default variant (white logo) never showed.

Reproduced by wrapping the board in `<iframe sandbox="allow-scripts">` (UNVERIFIED that the panel uses exactly this sandbox, but the symptoms matched 1:1):
- The board gets an opaque origin, so `contentDocument` of its same-server child frames is null: no injection.
- Opaque origin also makes every font and `type="module"` script fetch a CORS request: `Access to font ... from origin 'null' has been blocked by CORS policy`. The real pages lose their font and their JS (the map page renders nothing).

Fix that worked and was verified by clicking buttons inside the sandboxed wrapper:
1. Scratch copies of each real page (`mockup-*.html`, same directory so relative paths hold) with one extra `<script defer src="/mockup-inject.js">` (defer matters: in `<head>` without it, `document.body` is null).
2. The injected script applies variants on `postMessage` from the board and posts `{mk:'ready'}` to `parent` on load; the board answers `ready` with the current state and broadcasts on every click. postMessage works across opaque origins.
3. A scratch static server identical to the project's but adding `Access-Control-Allow-Origin: *`, run as an `ephemeral` supervised-run entry, so fonts and module scripts load under the opaque origin.

## Approach
Add a short "Iframing real pages into the panel" note to `C:\Users\tecno\.claude\skills\mockup\SKILL.md` step 3/5 (and/or `skills/preview/SKILL.md`): never rely on `contentDocument` across the panel boundary; use page copies plus a postMessage inject script, served with a CORS header; verify inside an `<iframe sandbox="allow-scripts">` wrapper, not a plain tab, before pushing. Optionally first confirm the panel's real sandbox attributes from the Conductor app source so the note states fact, not inference.

## Acceptance
- The mockup skill text tells a future session to verify in a sandboxed wrapper and names the postMessage + CORS pattern.
- A board built from the note works in the panel on the first push (buttons change frames, fonts load).
