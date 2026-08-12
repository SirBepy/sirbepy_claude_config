# Decide whether to formalize the framer test loop as an invokable skill

**Type:** skill-improvement

## Goal

Decide whether the `~/.claude/skills/framer/` folder should become a full invokable `/framer` skill (with a SKILL.md trigger) or stay as the current plain file set. Joe raised the idea this session and rated the full edit-automation version 4/10; the lean version (versioned source-of-truth file + test harness, manual edit/publish) is what got built.

## Context

Built this session in `~/.claude/skills/framer/` (a git repo, uncommitted): `zirtue-biller-landing.custom-code.html` (source of truth for the Framer Site Settings > Custom Code > End of body field), `test-biller-events.js` (Playwright harness that drives a published biller page and verifies the Amplitude events), and `README.md` (the loop + gotchas). Framer has NO API to write the custom-code field (confirmed: Server API does publish/deploy only; Plugin API writes a separate plugin-owned slot), so editing stays manual paste + publish. The rating's verdict: keep test-only automation, skip editor automation.

## Approach

- Option A: leave as plain files (current state). Claude reads/edits the .html when asked, hands Joe the paste chunk, runs the harness. No SKILL.md.
- Option B: add a lightweight SKILL.md so `/framer` triggers the loop explicitly (edit source-of-truth â†’ emit Conductor blockquote â†’ Joe publishes â†’ run harness â†’ report). Low effort; makes the workflow discoverable/repeatable.
- Either way: commit the folder to the `~/.claude` git repo (Joe said "dont commit the framer stuff yet" this session â€” get his go first).

## Acceptance

- A decision recorded (plain files vs invokable skill), and if Option B, a SKILL.md written following the skill-authoring conventions; folder committed to ~/.claude once Joe approves.

## Notes

- Dropped via /cleanup-todos 2026-08-11: already done - the /framer skill exists at zng-app\.claude\skills\framer\SKILL.md. Confirmed by dev 2026-08-11.
