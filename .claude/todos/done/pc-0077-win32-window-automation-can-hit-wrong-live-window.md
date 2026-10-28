<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=0d57d3ce -->
# No documented rule against raw Win32 mouse/window automation on the dev's live desktop

**Type:** skill-improvement
**Origin:** ai

## Goal

Add an explicit global rule (CLAUDE.md or a `~/.claude/refs/` doc referenced from it) against
driving raw OS-level window/mouse/keyboard automation (`SetForegroundWindow`, `MoveWindow`,
`mouse_event`/`SendInput`, `SendKeys`) against the dev's actual live desktop windows to grab a
screenshot or verify UI state - as opposed to an isolated, purpose-launched browser instance.

## Context

2026-08-10, zng-biller session: needed to screenshot a live `flutter run -d chrome` window (opened
for the dev to review) to self-verify a styling fix before reporting back. Used PowerShell +
`user32.dll` p/invoke (`GetWindowRect`, `SetForegroundWindow`, `MoveWindow`, `mouse_event`) to
locate the Chrome window by process id, resize/reposition it, and scroll it via a simulated mouse
wheel, then screenshotted via `Graphics.CopyFromScreen`.

The `SetForegroundWindow` + `mouse_event` step silently acted on a DIFFERENT window than intended -
the screenshot came back showing the dev's Claude Conductor chat list (other sessions, unrelated
content), not the Chrome window. Root cause not fully diagnosed, but plausible causes: Windows can
silently refuse `SetForegroundWindow` for a background process without an error return, so a
later `mouse_event`/`SendKeys` call lands on whatever window actually has focus (which may be
unrelated); multi-monitor coordinate confusion is a secondary risk (this machine has a rotated
portrait second monitor at negative Y coordinates).

No existing memory or CLAUDE.md rule covers this - the closest is
`reference_flutter_web_playwright_interaction` / `reference_biller_flutter_web_screenshot`, both
scoped to Flutter-canvas/DWDS quirks inside an ISOLATED Playwright-launched browser, not raw
OS-level automation against the dev's actual live windows. This is a distinct, more serious risk
class: acting on the wrong window can read/screenshot/click unrelated private content, not just
render a broken test.

The session caught its own mistake (deleted the screenshot unread, apologized, stopped touching
the dev's screen), but only after the fact - there was no upfront rule that would have steered
away from the raw-automation approach in the first place.

## Approach

Add a rule along these lines (exact wording/placement to whoever picks this up - likely
`~/.claude/CLAUDE.md` under a safety/process section, or a new `~/.claude/refs/` doc):

- Never drive OS-level window-focus, mouse, or keyboard automation (`user32.dll` p/invoke,
  `SendKeys`, raw `SendInput`) against a window that is the dev's own live application instance -
  only against an isolated, Claude-launched, disposable browser/process (e.g. a fresh
  `playwright-core` `launchPersistentContext` with its own profile dir, or a purpose-built release
  build served on a throwaway port) that cannot collide with anything the dev is actually looking
  at or working in.
- If the dev's live window genuinely must be screenshotted (rare - e.g. debugging something that
  only reproduces in their exact session/profile), ask first and have the dev confirm the target
  window is focused, rather than programmatically hunting for and focusing it.
- Consider whether `~/.claude/refs/flutter-web-playwright.md` (or wherever the Flutter/Playwright
  screenshot guidance lives) should cross-reference this rule so a future session reaching for
  "screenshot the running app" doesn't reinvent the raw-Win32 approach.

## Acceptance

- A grep-able rule exists that a future session would hit before attempting raw window automation
  on a live dev-owned window.
- The rule explicitly distinguishes "isolated Claude-launched browser instance" (fine) from "the
  dev's actual open window" (not fine without asking first).

## Notes

Origin is `ai` - the dev never asked for this rule; it was surfaced by Claude's own retrospective
after catching its own mistake mid-session. The incident itself was disclosed to the dev in-session
(not hidden), and the accidental screenshot was deleted without being inspected further.
- completed, commit 39029b7
