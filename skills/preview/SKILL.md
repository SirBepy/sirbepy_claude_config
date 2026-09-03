---
name: preview
description: Triggers on /preview only. Pushes a static HTML mockup, one or more markdown files/a directory rendered into a single navigable page, or one or more images inlined as a gallery page, into Claude Conductor's in-app preview panel via its localhost hook endpoint - replacing the localhost-server + browser-tab flow and, for images, replacing SendUserFile in a session that doesn't have it.
argument-hint: "<file.html | file.md... | image.png... | dir | inline html> [--slug <name>] [--title <text>]"
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

**Same slug = refresh in place.** Re-pushing with the identical `slug` REPLACES the live entry in Conductor's preview panel (version increments) instead of piling up a new one. This is the loop: edit the HTML file, re-run `/preview <file>` with the same default/explicit slug, the panel updates live. A new or omitted slug instead APPENDS a fresh snapshot to the history rail - use that only when the dev explicitly wants to keep an old version around for comparison.

Because the default slug is derived deterministically from the filename, just re-running `/preview <same-file>` after an edit already does the right thing with no flags needed.

## Markdown branch

When the input is one or more `.md` paths, or a directory of them, render first, then fall through to the same HTML steps below - there is no second delivery path.

1. Run the renderer to produce one self-contained HTML file: a sidebar listing each input document plus an anchor nav of that document's own headings, tables/code blocks/nested lists/links rendered, styling centralised in the script (never per-session).
   ```powershell
   python "C:\Users\tecno\.claude\skills\preview\render_markdown.py" <path.md> [<path2.md> ...] [--title "<text>"] [--out "<out.html>"]
   ```
   It prints the HTML file's path on success. Directories are expanded to their `.md` files automatically (recursive, sorted). Images are never inlined - the hook endpoint's ~2MB cap (step 4 below) makes that the wrong default, so a plan referencing local images keeps plain `<img>` links, not base64 data.
2. Re-running on the same input set produces the same default `--out` path and the same default slug (derived from the first path), so it refreshes the existing panel entry per the iterate-in-place convention below, not a new one.
3. Take the printed HTML path and continue at step 1 of the HTML steps below exactly as if it were a hand-written mockup file - same POST, same slug/title flags, same response handling.

## Image branch

When the input is one or more image paths, or a directory of them, build a gallery HTML page first, then fall through to the same HTML steps below - this is the path for "show Joe this screenshot" when the session has no `SendUserFile` tool.

1. Expand a directory arg to its `.png/.jpg/.jpeg/.gif/.webp` files (sorted) first. Then inline them, capping by RAW byte size before encoding (base64 adds ~33%, so a 1.5MB raw budget lands just under the endpoint's ~2MB cap): once a file would push the running total over budget, drop it and every file after it, and report every dropped filename - never truncate what made it in, and never let the POST hit 413.
   ```powershell
   node -e 'const fs=require("fs");const path=require("path");const files=["C:/path/shot1.png","C:/path/shot2.png"];const mime={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp"};const BUDGET=1.5*1024*1024;let used=0,included=[],dropped=[];for(const f of files){const size=fs.statSync(f).size;if(used+size>BUDGET){dropped.push(f);continue;}used+=size;included.push(f);}const figs=included.map(f=>{const ext=path.extname(f).toLowerCase();const b64=fs.readFileSync(f).toString("base64");return "<figure><img src=\"data:"+(mime[ext]||"image/png")+";base64,"+b64+"\" style=\"max-width:100%\"><figcaption>"+path.basename(f)+"</figcaption></figure>";}).join("\n");const html="<!doctype html><html><body style=\"font-family:sans-serif\">"+figs+"</body></html>";fs.writeFileSync("C:/tmp/preview-images.html",html);console.log("out:","C:/tmp/preview-images.html","included:",included.length,"dropped:",dropped);'
   ```
   Edit the `files` array for the actual paths, then tell the dev about any `dropped` entries before pushing.
2. Default slug/title derive from the first image path's stem, or the directory name for a directory input, same convention as the markdown branch.
3. Take the written HTML path and continue at step 1 of the HTML steps below exactly as if it were a hand-written mockup file.

## Steps

1. Read the HTML (from the file, or use the inline text given - for markdown input this is the file the markdown branch just produced).
2. POST it to Conductor's hook endpoint, including `session_id` from the `$CLAUDE_CODE_SESSION_ID` env var (always set inside a Conductor-hosted terminal session). This is required, not optional - the panel scopes previews to the chat that pushed them (Joe, 2026-07-20: previews must only show up in the chat that pushed them, not globally). Omitting `session_id` means the push will never be visible in any chat's panel.

   `POST http://127.0.0.1:27182/hooks/preview`
   Body: `{ "title": string, "slug"?: string, "html": string, "source": "terminal", "session_id": string }`

   **Primary: Node body-builder + curl.exe POST** (reliable string escaping on a large HTML string - write the JSON to a temp file, then POST that file so quoting/escaping isn't hand-rolled):
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
- Don't invent a new slug on every push "to be safe" - that defeats the iterate-in-place loop and litters the history rail. Reuse the derived/given slug across edits of the same file.
