---
name: preview
description: Pushes an HTML mockup, markdown, or images into Conductor's in-app preview panel. Replaces local server or SendUserFile.
argument-hint: "<file.html | file.md... | image.png... | dir | --manifest pairs.json | inline html> [--slug <name>] [--title <text>]"
---

# /preview

> Push HTML straight into Conductor's preview panel. No server, no browser tab.

## When to use

Manual trigger only, `/preview <file-or-html>`. For a STATIC HTML mockup (no build step, no framework) that the dev just wants to look at, for one or more markdown files (a plan, a spec, a directory of both) that the dev wants to read as a rendered page instead of opening in an editor, or for one or more images (e.g. `.for_bepy/screenshots/` captures) that need to reach Joe in a session with no `SendUserFile` tool. Not a replacement for `/supervised-run` when the preview needs a real dev server (Vite, Flutter web, etc.) - this is for the plain-HTML case `/mockup`'s standalone-file branch and ad-hoc scratch HTML already produce.

## Input

- **File path** (typical): an existing `.html` file, e.g. one just written to `.for_bepy/mockups/`.
- **Markdown path(s) or a directory**: one or more `.md` files, or a directory containing them (e.g. a plan plus its specs). Render first (see the markdown branch below), then push the result exactly like an HTML file.
- **Image path(s) or a directory**: one or more `.png/.jpg/.jpeg/.gif/.webp` files, or a directory containing them. Inlined into a gallery page first (see the image branch below), then pushed like an HTML file.
- **Inline HTML**: raw markup passed directly as the argument, for a quick one-off with no file.
- `--slug <name>` (optional): stable id for the entry. Default: derive from the filename (lowercase, non-alphanumeric -> `-`), e.g. `mockup-ring-preview.html` -> `mockup-ring-preview`. Inline HTML with no slug given gets a short generated one - ask the dev for a slug if they'll likely iterate on it (see below). For markdown or image input, default slug derives the same way from the first path (file stem, or directory name).
- `--title <text>` (optional): default is the filename, or a short label for inline HTML. For markdown or image input, default is the first path's stem/directory name.

## The iterate-in-place convention (the whole point)

**Same slug = refresh in place.** Re-pushing with the identical `slug` REPLACES the live entry in Conductor's preview panel (version increments) instead of piling up a new one, and the page it replaced is kept: the panel's version picker (beside the preview's name) lists "Latest" plus the previous 5 versions, so the dev can go back and look. This is the loop: edit the HTML file, re-run `/preview <file>` with the same default/explicit slug, the panel updates live. A new or omitted slug instead adds a separate preview to the panel's name picker - use that only for a genuinely different page (a different mockup, an alternative to compare side by side), never to keep an old version, which the same slug already does. The panel follows a push only while the dev is looking at the latest page of that preview; if they are on an older version or another preview, it stays put and dots the picker.

Because the default slug is derived deterministically from the filename, just re-running `/preview <same-file>` after an edit already does the right thing with no flags needed.

## The page standard (applied by the panel, not by you)

Every preview is a real HTML page, and Conductor's panel puts a **template** around it, so a push looks the same whichever producer sent it (`/preview`, `/mockup`, the `show_preview` tool). Do not hand-roll body padding, `max-width`, a viewport meta or zoom handling: the panel adds them.

- **Default template `page`:** body gets a centered column (`max-width: 1040px`) with padding that is 12px on a phone and grows to 28px on a wide panel, `system-ui` type at 1.55 line height, images capped to the column, and a viewport meta if the page has none. A bare fragment (no `<html>`/`<body>`) is wrapped in a dark page first.
- **Your own CSS wins.** The template's rules have zero specificity, so a page that sets its own `body { padding }`, `max-width` or `font-family` keeps it. `body { margin: 0 }` alone still leaves the template's padding.
- **Opt out with `<meta name="preview-template" content="bare">`** in `<head>` for a page that owns its whole layout: a sidebar-and-content render (`render_markdown.py` already does this), an app-shell mockup, or a `show_preview` card whose only content is an `<iframe>` of another page (otherwise the card pads around the frame and the framed page pads again). Unknown template names fall back to `page`.
- **Zoom is built into every pushed page:** two-finger pinch and double-tap on a phone, Ctrl+wheel (a trackpad pinch too) and Ctrl +/-/0 on desktop. The page zooms, the panel chrome does not, and scrolling stays native. Do not add zoom buttons or a pinch handler.
- "Open in browser" writes the page with the same template, so it matches the panel.
- A bundled app-CSS board (`/mockup`'s `bundle-board.mjs`) re-applies the template after its bundled CSS, because the app's own `html, body { padding: 0 }` reset would otherwise win; a board override must be written `html body.<root> { ... }`.

## Markdown branch

When the input is one or more `.md` paths, or a directory of them, render first, then fall through to the same HTML steps below - there is no second delivery path.

1. Run the renderer to produce one self-contained HTML file: a sidebar listing each input document plus an anchor nav of that document's own headings, tables/code blocks/nested lists/links rendered, styling centralised in the script (never per-session). The page is responsive by default (phone-readable in the preview panel): under 700px the sidebar becomes a collapsible "Contents" block at the top, tables become labelled cards, and it follows `prefers-color-scheme`.
   ```powershell
   python "C:\Users\tecno\.claude\skills\preview\render_markdown.py" <path.md> [<path2.md> ...] [--title "<text>"] [--out "<out.html>"]
   ```
   It prints the HTML file's path on success. Directories are expanded to their `.md` files automatically (recursive, sorted). Images are never inlined - the hook endpoint's ~2MB cap (step 4 below) makes that the wrong default, so a plan referencing local images keeps plain `<img>` links, not base64 data.
2. Re-running on the same input set produces the same default `--out` path and the same default slug (derived from the first path), so it refreshes the existing panel entry per the iterate-in-place convention below, not a new one.
3. Take the printed HTML path and continue at step 1 of the HTML steps below exactly as if it were a hand-written mockup file - same POST, same slug/title flags, same response handling.

## Image branch

When the input is one or more image paths, or a directory of them, build a gallery HTML page first, then fall through to the same HTML steps below - this is the path for "show Joe this screenshot" when the session has no `SendUserFile` tool.

1. Run the builder to produce one self-contained HTML file, same pattern as the markdown branch's `render_markdown.py`:
   ```powershell
   python "C:\Users\tecno\.claude\skills\preview\build_gallery.py" <image...|dir> [--slug <name>] [--title "<text>"] [--budget-mb 1.5] [--check] [--post]
   ```
   It expands a directory arg to its `.png/.jpg/.jpeg/.gif/.webp` files (sorted), inlines them capping by RAW byte size before encoding (base64 adds ~33%, so the 1.5MB default raw budget lands just under the endpoint's ~2MB cap), and once a file would push the running total over budget drops it and every file after it. It prints the output HTML path and `included: N dropped: [...]` - report every dropped filename to the dev before pushing, never silently truncate. On a budget drop it also prints a ready-to-run follow-up command for the remainder (same script, remaining files, `--slug <slug>-2`), so a second gallery is copy-paste, not re-authoring. The built page ships a click-to-zoom lightbox by default (pure inline CSS+JS, no external deps): clicking any thumbnail opens it full-size in an overlay, left/right arrow keys or the on-screen `‹`/`›` arrows step between images, and Esc or a click on the backdrop closes it. Pass `--check` to load the built HTML headless before posting and fail (non-zero exit, printing the page error) if it throws - catches the class of bug where a page renders fine from `file://` but errors once served through the panel's own page. Pass `--post` to have the script send the POST itself (same body shape as step 2 below, reading `session_id` from `$env:CLAUDE_CODE_SESSION_ID`) and skip straight to its printed `HTTP <status>: <body>` line instead of doing step 2 by hand.
   - **No-Python fallback** (Python unavailable): build the gallery by hand with the inline node-builder-plus-curl ritual - write a `.mjs` body-builder to a scratch file (image attributes embed `"`, so this can never be a quote-free `node -e` argument; `\"` inside a native-command argument gets stripped by PowerShell 5.1 before node runs, leaving `SyntaxError: Unexpected token ':'`), run it, delete it:
     ```powershell
     # Write to C:\tmp\preview-build.mjs (via the Write tool, not shell redirection):
     #   import fs from "fs";
     #   import path from "path";
     #   const files = ["C:/path/shot1.png", "C:/path/shot2.png"];
     #   const mime = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp" };
     #   const BUDGET = 1.5 * 1024 * 1024;
     #   let used = 0, included = [], dropped = [];
     #   for (const f of files) {
     #     const size = fs.statSync(f).size;
     #     if (used + size > BUDGET) { dropped.push(f); continue; }
     #     used += size;
     #     included.push(f);
     #   }
     #   const figs = included.map(f => {
     #     const ext = path.extname(f).toLowerCase();
     #     const b64 = fs.readFileSync(f).toString("base64");
     #     return `<figure><img src="data:${mime[ext] || "image/png"};base64,${b64}" style="max-width:100%"><figcaption>${path.basename(f)}</figcaption></figure>`;
     #   }).join("\n");
     #   const html = `<!doctype html><html><body style="font-family:sans-serif">${figs}</body></html>`;
     #   fs.writeFileSync("C:/tmp/preview-images.html", html);
     #   console.log("out:", "C:/tmp/preview-images.html", "included:", included.length, "dropped:", dropped);
     node C:\tmp\preview-build.mjs
     Remove-Item C:\tmp\preview-build.mjs
     ```
     Edit the `files` array for the actual paths, then tell the dev about any `dropped` entries before pushing.
2. Default slug/title derive from the first image path's stem, or the directory name for a directory input, same convention as the markdown branch.
3. If `--post` wasn't used, take the written HTML path and continue at step 1 of the HTML steps below exactly as if it were a hand-written mockup file. `build_gallery.py` also accepts a single existing `.html` file in place of image paths - it passes the file through unchanged and, with `--post`, pushes it the same way, so a repeatedly-republished Code-mode mockup can go through this same script instead of a hand-typed body-builder each time. `--check` works on this passthrough file too (same headless-load-before-posting guard), which is the case it was added for: a mockup that re-pushes the same HTML many times over a session, where a late edit introducing an inline-script error is easy to miss without a render check.

## Before/after branch (manifest)

Use this when Joe must judge several changes by looking (keep/drop a UI sweep, compare old and new screens). A flat gallery of filenames makes him read words instead of comparing pictures. Write a manifest JSON (via the Write tool), then build:

```powershell
python "C:\Users\tecno\.claude\skills\preview\build_gallery.py" --manifest <manifest.json> [--slug <name>] [--title "<text>"] [--budget-mb 1.5] [--check] [--post]
```

Manifest: a JSON list, or `{"title": "...", "items": [...]}`. Each item is `{"id": "fix-3", "title": "Tab bar wraps", "note": "one line on what changed", "shots": [["Before", "shots/3-before.png"], ["After", "shots/3-after.png"]]}`. Shots are `[caption, path]` pairs shown left to right in the order given, so a variant is a third pair; relative paths resolve against the manifest's directory. The script validates before building and exits 1 naming the item and shot at fault (missing file, duplicate id, malformed shot).

- Each item becomes a numbered section (badge `1..N` in manifest order). Number the question card's option labels the same way, so "keep 3, drop 5" maps to the badges Joe sees.
- PNG/JPEG shots are re-encoded to WebP through `ffmpeg` (PNG screenshots shrink several-fold; 28 phone-width shots came to ~610 KB), keeping the original when WebP is not smaller or `ffmpeg` is missing. GIF and WebP are never re-encoded. The same lightbox as the flat gallery is reused, stepping through every shot in order.
- The budget drops whole items, never half a pair: from the first item that would overflow, it and every later item are dropped, listed in `dropped: [...]`. Report them to the dev and put them in a second manifest (`--slug <slug>-2`).
- With `--post` the script also prints `render-url: http://127.0.0.1:27182/hooks/preview-render/<id>` on a 200. The panel alone is not enough: Joe answers from the chat and may never open the panel (2026-10-13, he answered a keep/drop card with "id need to see a before and after view" because the gallery sat unseen in the panel).
- **When the gallery precedes a question, show it inline first.** Send a `show_preview` card whose HTML is an iframe to that `render-url` (with `<meta name="preview-template" content="bare">` in its head, so the card does not pad around the frame) immediately before the question, then ask. Do not rely on the panel push alone.
- **A render-url is short-lived.** (App facts below are sourced from todo pc-1286, claude_usage_in_taskbar commit 10d2e4b9, 2026-10-30; not verifiable from this repo.)
  - It lives in the daemon's memory only, in a 64 MiB LRU of rendered pages. After a daemon restart, or after a lot of later rendering, an inline card iframing an old render-url goes blank.
  - `show_preview` of a card whose iframe targets a render id the daemon no longer holds is refused (HTTP 410 from `/hooks/preview`) and the session sees a tool error. The check runs at push time only. On that error, re-run `build_gallery.py --post` for a fresh `render-url` and call `show_preview` again. Never ignore the error.
  - A card that must survive a daemon restart cannot iframe a render-url: inline the image as a `data:` URL `<img>` instead.
  - If the inline iframe card shows black or white, re-check the page with `build_gallery.py --check` before blaming the page.

## Steps

1. Read the HTML (from the file, or use the inline text given - for markdown input this is the file the markdown branch just produced).
2. POST it to Conductor's hook endpoint, including `session_id` from the `$CLAUDE_CODE_SESSION_ID` env var (always set inside a Conductor-hosted terminal session). This is required, not optional - the panel scopes previews to the chat that pushed them (Joe, 2026-07-20: previews must only show up in the chat that pushed them, not globally). Omitting `session_id` means the push will never be visible in any chat's panel.

   `POST http://127.0.0.1:27182/hooks/preview`
   Body: `{ "title": string, "slug"?: string, "html": string, "source": "terminal", "session_id": string }`

   **Primary: Node body-builder + curl.exe POST** (reliable string escaping on a large HTML string - write the JSON to a temp file, then POST that file so quoting/escaping isn't hand-rolled). This exact one-liner only survives PowerShell because every JS string inside it is single-quoted with no embedded `"` - PowerShell 5.1 strips `\"` out of a double-quoted native-command argument before node ever sees it. The moment a payload needs an embedded `"` (e.g. building HTML with double-quoted attributes), switch to the `.mjs` file variant shown in the Image branch below instead of trying to escape it inline:
   ```powershell
   node -e "const fs=require('fs');const html=fs.readFileSync('C:/path/to/mockup.html','utf8');fs.writeFileSync('C:/tmp/preview-body.json',JSON.stringify({title:'Ring preview',slug:'mockup-ring-preview',html,source:'terminal',session_id:process.env.CLAUDE_CODE_SESSION_ID}))"
   curl.exe -X POST http://127.0.0.1:27182/hooks/preview -H "Content-Type: application/json" --data-binary "@C:\tmp\preview-body.json"
   ```

   **No-Node fallback: PowerShell `ConvertTo-Json`** (build the body via `ConvertTo-Json` so the HTML is escaped correctly - never hand-splice it into a JSON string). Known quirk: `ConvertTo-Json` sometimes wraps a large raw string value as `{"value": "..."}` instead of a plain string, which the daemon then rejects with "html: invalid type: map, expected a string" - if that happens, use the Node builder above instead:
   ```powershell
   $html = Get-Content -Raw -Path "C:\path\to\mockup.html"
   $body = @{ title = "Ring preview"; slug = "mockup-ring-preview"; html = $html; source = "terminal"; session_id = $env:CLAUDE_CODE_SESSION_ID } | ConvertTo-Json
   Invoke-RestMethod -Uri "http://127.0.0.1:27182/hooks/preview" -Method Post -ContentType "application/json" -Body $body
   ```

3. **Response 200 `{ "id": "<id>" }`** -> success. Tell the dev it's live in Conductor's preview panel, and that re-running `/preview` on the same file will refresh it in place (same slug). Do NOT open a browser tab or start a server.
4. **Response 413** -> HTML exceeds ~2MB. Trim it (inline a smaller asset, drop embedded base64 images) and retry; don't silently fall back to the old flow for this case, the content itself is the problem.
5. **Connection refused** -> Conductor's app/daemon isn't running. Say so plainly ("Conductor isn't reachable on 127.0.0.1:27182, falling back to opening the file directly"), then fall back to the OLD flow: open the file directly.
   ```powershell
   Start-Process "C:\path\to\mockup.html"
   ```
6. **Any other status** (400, 401/403, 500, etc.) -> report the exact status code and response body to the dev verbatim. Do not retry silently and do not assume success - an unrecognized response means something changed on the daemon side that this skill doesn't yet account for.

## Rules

- Never open a browser or spin up a localhost server when the push succeeds - that's the exact flow this skill replaces.
- `source` is always `"terminal"` for this skill (the app also accepts `"chat"` pushes from elsewhere; that's not this path).
- Don't invent a new slug on every push "to be safe" - that defeats the iterate-in-place loop and litters the preview picker and loses the version history. Reuse the derived/given slug across edits of the same file.
