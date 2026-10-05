<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hook hits (259, 357, 41, 43, 489) share only generic words (step/check/verify/live); 43 is the closest (/mockup-related) but is about autopilot disposal policy, a different concern -->
# /mockup's step 6 "gated selectors" check should also verify the live render call site, not just the stylesheet

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/mockup/SKILL.md` step 6's "gated selectors" check only greps the reused STYLESHEET for a
selector's ancestor gate. It should also confirm the class the mockup is reusing is actually
emitted by the component's current render function - a stylesheet can define rules for a visual
mode that is unconditionally dead at runtime while still compiling and reading as plausible.

## Context

In a `claude_usage_in_taskbar` session (2026-10-01), a `/mockup` round of the sidebar's frozen-chat
indicator was built against the "classic" two-line row CSS in `session-list.css`/
`session-avatar.css`, because reading those files suggested that was the row shape. Step 6's gated-
selector check passed cleanly - the classes existed, compiled, and rendered something plausible.
Joe rejected it outright: "this isnt a good mockup, cuz its not showing the sidemenu the way mine
looks." Root cause, found only by reading `src/views/sessions/sidebar-rows.ts`: every row
(`sessionRowOptions`/`draftRowOptions`/`parkedRowOptions`, all via `buildRowOptions`) unconditionally
appends a `row-portrait` class - there is no toggle left, despite `session-row-portrait.css`'s own
header comment still describing it as a "Settings > Appearance > Chat row style" option. The
"classic" row CSS was vestigial: present, well-formed, and completely unreachable.

Full writeup and the generalizable lesson: `memory/feedback_verify_render_call_site_before_mockup.md`
in that project's Auto Memory store (not committed to the project repo - per-project memory lives
outside git).

## Approach

In `skills/mockup/SKILL.md` step 6's "Gated selectors" bullet (currently: "grep the reused
stylesheet(s) for the selectors being copied..."), add: before trusting a component's CSS file(s) as
the source of truth for what a component currently looks like, grep the component's actual render
function (the TS/JS/Dart that assembles the class list or conditional markup) for the literal class
names/branches being reused. If a CSS file's own header comment mentions a toggle/setting/mode, treat
that as a flag to verify the toggle still has a live code path - do not assume the "other" mode's
CSS is still reachable just because the file still exists and parses.

Consider whether this is better phrased as its own numbered check (parallel to the existing three
non-negotiable checks: gated selectors, computed style, geometric claims) rather than folded into
the existing gated-selectors bullet, since it catches a different failure mode (dead code path, not
a scoping miss).

## Acceptance

- Step 6 (or a new adjacent check) explicitly calls out verifying the render call site's actual
  class-emission logic before reusing a component's CSS file(s) wholesale.
- The addition names the specific failure mode (a CSS file describing a legacy/alternate mode that
  is unconditionally dead at runtime) so a future reader understands why this differs from the
  existing ancestor-scoping gated-selector check.

## Notes

This is a skill-doc change only - no code in `skills/mockup/` itself needs editing beyond the
SKILL.md text.
