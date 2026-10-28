<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 969 (done) is about the Spliced-CSS branch's EXISTENCE, which this todo assumes and builds on; 237 is about scratch-file cleanup ownership. Neither is about the branch-selection verification gap this todo describes. -->
# /mockup's branch-selection step picks Spliced-CSS on an unverified conflict assumption

**Type:** skill-improvement
**Origin:** ai

## Goal
Tighten `skills/mockup/SKILL.md` step 2's branch-selection table so the Spliced-CSS branch is only
chosen when a live dev-server conflict is actually confirmed, not merely possible.

## Context
2026-10-18, `claude_usage_in_taskbar` session e32d5862 (mobile Chats overhaul). The skill's step 2
picks the Spliced-CSS branch when "the dev server the mockup would otherwise run in is the dev's
own live workspace right now." For a critique-driven mockup of an existing screen (Joe had just
sent a real screenshot of his phone's Chats screen from the INSTALLED production app, not a dev
session), I chose Spliced-CSS anyway, reasoning from the mere existence of `cargo tauri dev`
tooling in the repo rather than checking whether Joe actually had a conflicting dev session
running. He didn't - there was no live-workspace conflict at all.

Joe rejected the resulting mockup as hand-typed markup, "not really comparable," and the
real-component branch worked cleanly and was approved immediately once used. See this project's
own memory `feedback_mockup_real_component_over_spliced_css_for_critique_driven_ui.md` for the
full incident and the broader lesson (prefer real-component for critique-driven work on an
existing screen); this todo is specifically about the skill's own branch-selection text, which
currently has no instruction to verify the conflict before assuming it.

## Approach
In step 2's Spliced-CSS trigger condition, add a concrete verification step before selecting that
branch over Real-component: check `list_peers`/ask whether the dev's own session (or a peer) has
the relevant dev server actually running, rather than inferring conflict risk from the project
having dev-server tooling at all. Consider whether the condition should default to Real-component
when verification is inconclusive, given Real-component's fidelity advantage and that the
live-workspace risk is the only reason Spliced-CSS exists as a separate branch.

## Acceptance
`skills/mockup/SKILL.md` step 2 names a concrete check (not an assumption) for the live-workspace
conflict before routing to Spliced-CSS over Real-component.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): mockup step 2 confirms a live-workspace conflict (list_peers, supervisor list plus dev-port listen check, or the dev's own words) before the Spliced-CSS branch; inconclusive defaults to Real-component.
