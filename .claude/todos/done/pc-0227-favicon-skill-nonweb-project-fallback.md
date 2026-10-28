<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /favicon skill has no fallback for non-web "personal tooling" repos

**Type:** skill-improvement

## Goal

`skills/favicon/SKILL.md` + `skills/favicon/platforms/html.md` should recognize projects that
aren't web apps at all (no `index.html`, no bundler, nothing to add `<link rel="icon">` tags to)
and place favicon files where the actual consumer expects them, instead of blindly applying the
generic HTML platform's `assets/images/favicon.svg` canonical path.

## Context

2026-08-01, setting up a favicon for `C:\Users\tecno\.claude` itself (Joe's global Claude Code
config/skills repo) so it shows an icon in `claude_usage_in_taskbar`. That app's icon scanner
(`src-tauri/src/ipc/project_icons.rs`, `ICON_CANDIDATES`) walks a project's repo root looking for
exact filenames â€” `icon.svg`, `favicon.svg`, `favicon.ico`, etc. â€” directly at project root (or a
short list of common subpaths). It does not read HTML `<link>` tags at all; it just scans the
filesystem.

`skills/favicon/platforms/html.md`'s canonical path is `assets/images/favicon.svg` +
`favicon.ico` at root, on the assumption there's an `index.html` to wire up. `.claude` has no
`index.html` â€” it's not a web project, Step 0's platform detection has no signal for "plain
config/tooling repo with no web entry point at all" and falls through to the `html` platform
regardless, which is right about `favicon.ico` staying at root but wrong about `favicon.svg`/
`favicon.png` living under `assets/images/`.

Placing the SVG/PNG under `assets/images/` here would have made them invisible to
`claude_usage_in_taskbar` (not in its `ICON_CANDIDATES` list at all) while looking successful â€”
the skill would report done, nothing in `index.html` to break, and the actual goal (icon shows
up in the taskbar) silently fails. Deviated manually this session: put all three files
(`favicon.svg`, `favicon.png`, `favicon.ico`) directly at repo root instead.

## Approach

Add a platform signal ahead of the `html` fallback in Step 0: no `index.html` anywhere in the
project AND no bundler config (`vite.config.*`, `next.config.*`, `package.json` with a web
framework, `Cargo.toml` with `tauri`) â†’ treat as "non-web / tool repo" and use repo-root-only
canonical paths (`favicon.svg`, `favicon.png`, `favicon.ico` all at root, no `assets/` nesting,
Step 4 HTML update always skipped â€” there's nothing to wire up). Could live as a new
`platforms/non-web.md` spec, or as an explicit early branch in `SKILL.md` Step 0 before it falls
through to `html.md`.

## Acceptance

- Running `/favicon` fresh on a project with no `index.html` and no bundler config places all
  three favicon files at that project's root, not under `assets/images/`.
- Existing web-project behavior (Tauri/Next/React/Vite/plain-HTML-with-index.html) is unchanged.

## Notes

Not urgent â€” one-off manual workaround already shipped for `.claude` itself
(`favicon.svg`/`.png`/`.ico` committed at repo root, `.gitignore` updated with explicit
exceptions since it's an allowlist-style ignore file). This todo is only about making the skill
handle the next repo like this correctly without a manual detour.
- Dropped via /cleanup-todos 2026-08-11: one instance, already worked around manually. Confirmed by dev 2026-08-11.
