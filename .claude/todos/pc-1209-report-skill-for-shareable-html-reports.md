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

## Notes

- 2026-11-07: Joe picked: build now, one fixed self-contained HTML layout pushed via show_preview, layout settled through /brainstorm.
