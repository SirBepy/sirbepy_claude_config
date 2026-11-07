<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/72 is about screenshotting HTML comps for Claude's own inspection, not producing shareable reports -->
# A /report skill for shareable HTML reports

**Type:** skill-improvement
**Origin:** dev
**Summary:** A /report skill turns a requested report into one consistent, self-contained HTML page that publishes cleanly through Conductor.

## Why

"sometimes youll make me a /report (myb we should maek that a skill) and whatever that looks like is what we should share with others" (Joe, 2026-10-20). He was tentative about scope.

## Goal

Joe often asks Claude for a "report" and gets a one-off HTML page. He wants that to be a repeatable skill (`/report`) so reports look consistent and are ready to publish and share with others.

## Context

- Raised 2026-10-20 in the claude_usage_in_taskbar chat designing "Publish to claude.ai" (that repo's todo 1152). Joe: "sometimes youll make me a /report (myb we should maek that a skill) and whatever that looks like is what we should share with others".
- Conductor is getting a "Publish to claude.ai" button on preview-panel HTML. It uploads the page as-is (private claude.ai artifact via the CLI's built-in Artifact tool), so whatever the report skill renders is exactly what teammates see.
- Joe was tentative ("myb"), so confirm the scope with him before building.

## Approach

Run `/brainstorm`. Likely shape: a skill that turns a requested report into one self-contained HTML page with a consistent layout, pushed to the preview panel (`show_preview` in Conductor) so the publish button applies.

## Acceptance

- `/report <topic>` produces a consistent, self-contained HTML report in the preview panel.
- The page publishes cleanly through Conductor's Publish to claude.ai button.

## Decided

Decided by /loop-todos sub on 2026-11-07 (Joe asleep, no /brainstorm card).

- [x] [UX] Layout? - decided **header (kicker, title, subtitle, meta), summary box, optional stat tiles, numbered sections, optional next steps and open questions, optional sources footer**, because a reader who stops at the summary still gets the answer and a fixed order keeps every shared report recognisable.
- [x] [ARCH] How is the page produced? - decided **a JSON spec built into HTML by `skills/report/build_report.py`**, because a script makes the layout the same every time and testable, where hand-written HTML drifts per report.
- [x] [ARCH] Publish safety? - decided **inline CSS only, no script, no web font, no CDN, no image URL, no icon library, everything escaped**, because Publish to claude.ai uploads the page as-is and a published copy may be offline or sandboxed.
- [x] [UX] Icons? - decided **none (tone words OK/Watch/Problem plus colour instead of Phosphor)**, because Phosphor needs a CDN fetch, which the self-contained rule forbids.
- [x] [UX] Template? - decided **`preview-template` bare, own 860px column, light/dark, phone cards for tables, print CSS**, because the page owns its layout and the panel's padding would double up.
- [x] [TOOLING] Slash-only? - decided **`disable-model-invocation: true`**, because Joe invokes it as /report and it then costs no description budget.
- [x] [TOOLING] Push path? - decided **`show_preview` primary, `--post` via `preview/push_html.py` as fallback**, because the brief asks for show_preview and push_html already guards the session id.

## Notes

- 2026-11-07: Joe picked: build now, one fixed self-contained HTML layout pushed via show_preview, layout settled through /brainstorm.
- built: skills/report (SKILL.md, build_report.py, test_build_report.py); layout calls in ## Decided
