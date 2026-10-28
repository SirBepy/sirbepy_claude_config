<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1060 is about verifying against the render call site vs stale CSS (already folded into the skill's step 6 checks); 310/870 are unrelated (supervised-run teardown, Clockify overlap check). This is specifically about the sandboxed-iframe-panel verify step's trigger condition being scoped too narrowly to "frames a real page", missing a mockup's own internal iframe. -->
# 1204 - mockup skill's sandboxed-iframe verify rule is scoped too narrowly

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude/skills/mockup/SKILL.md`'s "Iframing real pages into the panel" section should cover
ANY iframe a mockup page creates, not only one that frames the project's own real routes.

## Context

2026-10-20, claude_usage_in_taskbar, account-chip mockup session: a mockup built a nested iframe
(via `srcdoc`) purely to simulate a real mobile `@media` breakpoint at an accurate width - nothing
to do with framing a real app page, the case the skill's existing warning is written for. Pushed
to Conductor's preview panel (which itself hosts the pushed page inside its own sandboxed iframe),
the nested iframe-in-sandboxed-iframe, combined with an external `<script src="https://unpkg.com/
...">` tag inside it, threw `Uncaught SyntaxError: Unexpected end of input` and broke the ENTIRE
preview - confirmed via the dev's own phone screenshot of the panel's "preview diagnostic" error
banner. The skill's `/preview`-push verification step (step 6, "actually look, don't assume the
wiring worked") was followed - screenshot taken via the standalone Playwright screenshot-helper,
which rendered fine - but that check used a PLAIN tab, not the sandboxed-iframe wrapper the
"Iframing real pages" section separately prescribes, and that section's own trigger condition
("when a board frames the project's own real pages") didn't fire because this iframe framed
nothing real.

## Approach

Edit `~/.claude/skills/mockup/SKILL.md`'s "Iframing real pages into the panel" section (or
promote its verification method into step 6 itself) so the sandboxed-wrapper check applies to
ANY `<iframe>` present in a mockup page before pushing, regardless of what it loads - a `srcdoc`
simulation, a same-origin scratch file, or a real app route. The actual fix that shipped for THIS
incident: drop the nested iframe, copy the real CSS rule's exact declared property values into a
mockup-only class applied unconditionally in the same document instead - worth citing as the
recommended fallback pattern when an iframe isn't load-bearing to what's being demonstrated.


## Notes

- Completed 2026-10-23 (loop-todos cycle 1): the iframe section now covers ANY iframe in a pushed page incl. srcdoc simulations, adds the copy-the-CSS-values fallback, and step 6 requires the sandboxed-wrapper check for any page with an iframe.