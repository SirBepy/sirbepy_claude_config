<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new, no other todo covers the /preview skill's render-url text -->
# /preview skill text must describe the render-url lifetime and the stale-id error

**Type:** task
**Origin:** ai
**Summary:** The /preview skill's "show it inline first" section matches what the app does after claude_usage_in_taskbar commit 10d2e4b9: a render-url lives in daemon memory and a stale one is refused.

## Why

The app-side fix for inline show_preview cards that went blank (claude_usage_in_taskbar pc-1441, commit 10d2e4b9, 2026-10-30) changed behavior the skill text describes. The skill lives in this repo so the app repo could not edit it.

## Goal

`skills/preview/SKILL.md` (about lines 94-95, the "show it inline first" rule) states the new facts.

## Context

- The daemon's render cache is now a 64 MiB byte-budgeted LRU (was 10 entries, which aged a gallery render-url out after ten later card renders). It is in memory only: after a daemon restart, or after a lot of rendering, an old inline card iframing a render-url goes blank.
- `show_preview` from a chat card whose iframe points at a render id the daemon no longer holds is refused (HTTP 410 from `/hooks/preview`), and the session sees a tool error. The check runs at push time only.
- Anything that must survive restarts should be inlined as a `data:` URL `<img>` (the workaround that worked on 2026-10-28).

## Approach

Keep "show it inline first" with the render-url iframe. Add: on that tool error, re-run `build_gallery.py --post` for a fresh render-url and call `show_preview` again, never ignore it; use a `data:` URL image for cards that must persist.

## Acceptance

The skill text says the three points above and nothing in it still implies a render-url is permanent.

## Notes

- Fixed in 249942f.
