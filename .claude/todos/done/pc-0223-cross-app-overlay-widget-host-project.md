<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# New project: a shared bottom-left widget-host app for other apps' overlays

**Type:** task

## Goal

A brand-new Tauri app whose whole purpose is hosting small always-on-top widgets in the
bottom-left corner of the screen. Instead of each app (claude_usage_in_taskbar, pomodoro-overlay,
future ones) shipping and maintaining its own floating overlay window, they'd each get a settings
toggle to render their overlay INSIDE this shared host app instead, with the host providing shared
customization (position, opacity, layout, whatever else comes out of the brainstorm) on top.

This is explicitly a someday/maybe - Joe wants to brainstorm it properly before any of this gets
built. Filed now purely so the idea doesn't get lost; do not start building the new project from
this file alone.

## Context

Filed 2026-07-28, in the middle of a session that had just mocked up and (per the matching todo/
session in claude_usage_in_taskbar) started implementing a reset-countdown popup for THIS app's
floating overlay. Joe floated the bigger idea mid-session: instead of every small utility app
building its own bottom-of-screen overlay independently, there could be one shared "widget host"
app that others plug into.

The two concrete existing overlays that would feed into this:
- `claude_usage_in_taskbar` (this repo) - `src/views/overlay/overlay.ts` +
  `src/shared/usage-dial.ts` (dial rendering, shared with the remote/phone header too) +
  `src/views/overlay/overlay.css`. Always-on-top transparent Tauri window, toggled from the tray,
  one dial per account.
- `pomodoro-overlay` (sibling project, `C:\Users\tecno\Desktop\Projects\pomodoro-overlay`) - a
  single-window Tauri app (`src/main.ts`) that IS itself an overlay/widget (a pomodoro timer),
  not a separate overlay-vs-dashboard split like this app has.

Joe's own words mid-brainstorm (paraphrased, keep as raw signal - not yet a decision):
- Bottom-left corner placement.
- Each source app keeps owning ITS OWN data/logic; only the overlay's rendering/hosting moves.
- The host should allow "a bunch of customization" (unspecified - this is exactly what needs
  brainstorming: per-widget vs global settings, theming, layout/arrangement, sizing).
- Other, currently-unbuilt projects should eventually be able to plug in too, not just these two.
- Open question Joe raised himself and didn't resolve: whether customization is defined only by
  the host, only by each source project, or both (host provides a customization framework, each
  project can extend/override it for its own widget). Needs a real brainstorm, not a guess.

## Approach

Do NOT start writing code from this file. When Joe picks this up:
1. Run a proper `/brainstorm` (or a longer design conversation - this is big enough it may
   warrant more than the usual gate-free single-pass) covering at minimum: how a source app's
   overlay content gets INTO the host (embedded webview per widget? IPC pushing HTML/DOM diffs?
   each source app ships a small manifest/plugin the host loads?), what "customization" concretely
   means and who owns which knob, whether this is one process with N renderer surfaces or truly
   separate processes coordinating, and what happens to each app's OWN overlay window/toggle once
   the host exists (removed? kept as a fallback/standalone mode?).
2. Only after that brainstorm converges, scaffold the new project (name TBD) and start porting.

## Acceptance

N/A yet - this is a pre-brainstorm placeholder, not an executable spec. Acceptance criteria get
written once the brainstorm above actually happens.

## Notes

The concrete, already-scoped piece of work that prompted this idea (a reset-countdown popup added
to claude_usage_in_taskbar's existing overlay hover panel) is NOT blocked on this and was
implemented directly in that session/repo instead of waiting on this bigger project.
- Dropped via /cleanup-todos 2026-08-11: self-declared someday/maybe placeholder with no acceptance criteria. Confirmed by dev 2026-08-11.
