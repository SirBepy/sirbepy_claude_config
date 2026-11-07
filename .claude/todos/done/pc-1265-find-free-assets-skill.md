<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits share only generic words (skill, instead, free); no existing asset-search skill or todo -->
# New skill: find free, license-checked assets (sprites, tilesets, icons, sounds) instead of making them

**Type:** skill-improvement
**Origin:** dev
**Summary:** A skill finds existing free art and sounds and reports each candidate's license, redistribution rights and fit, so Claude never draws assets itself.

## Why

"i dont want you making the assets at all... it costs too many tokens... i wanna make you good at searching for assets" (Joe, 2026-10-28).

## Goal

A `/find-assets` style skill that makes Claude good at locating existing free art (pixel sprites, tilesets, UI packs, sound effects) and reporting each candidate's license, redistribution rights and fit, so Claude never spends tokens drawing assets itself.

## Context

Joe, 2026-10-28, claude_usage_in_taskbar "Game city view" brainstorm: "i dont want you making the assets at all... it costs too many tokens and it can sometimes not be worth it... theres tons of free great assets out there, i wanna make you good at searching for assets (we should prolly build and update a skill for searching for free assets)". This is a standing cross-project preference: no AI-drawn or hand-drawn (SVG/CSS pixel) game art; find existing assets or use a free deterministic pipeline.

That session's research (sonnet subagents, web) produced a starter source map worth seeding the skill with:
- Kenney (kenney.nl): everything CC0, logo reserved.
- OpenGameArt: filter by license; many office/indoor packs are CC-BY-SA, not CC0.
- itch.io: LimeZu Modern Interiors/Office are cheap but forbid redistribution (local-only use).
- LPC / Universal LPC Spritesheet Generator: per-layer CC0/CC-BY/CC-BY-SA/GPL, exports a credits CSV.
- JIK-A-4 Metro City: CC0 characters.
- The Spriters Resource: rips, no license; fine only for local private use, never in a public repo or store build (Google Play IP policy bans video-game artwork).
- Prior art repos credit their sources (Pixel Agents, a16z AI Town, Stanford Smallville) and are a good lead for where good packs live.

## Approach

- Skill body: a source list per asset kind, a license triage table (CC0 / CC-BY / CC-BY-SA / GPL / "no redistribution" / unlicensed rip) with what each allows for public repo, app store, local-only.
- Always dispatch the search to a sonnet subagent (multi-query web research), return candidates with URL, license quote, art size, animation coverage, and a fit verdict.
- Encode the rule: Claude does not create art assets unless Joe explicitly asks for one in that session.
- Keep a living `sources.md` the skill appends to when a search finds a good new source ("build and update").

## Acceptance

- Invoking it for "cute pixel office characters with sit/typing animation" returns ranked, license-annotated candidates without Claude drawing anything.
- The no-asset-making rule is stated in the skill so it applies in every project.

## Notes

- built: skills/find-assets (SKILL.md, sources.md); design calls in ## Decided

## Decided

Decided by /loop-todos sub on 2026-11-07 (Joe asleep).

- [x] [ARCH] Invocation? - decided **model-invocable, not slash-only**, because the no-asset-making rule must apply in every project the moment a game needs art, and the description is 18 words / 95 chars so it fits the budget.
- [x] [ARCH] Search runs where? - decided **always a read-only sonnet subagent that must quote each license verbatim from the asset page**, because multi-query web research stays out of the main context and "license, I think" is how a bad pack ships.
- [x] [DATA] Shipping target? - decided **the brief fixes `public-repo` / `app-store` / `local-only` first (strictest likely when unstated) and a license-by-target table filters candidates**, because the same pack is fine local-only and illegal in a public repo.
- [x] [DATA] Free only? - decided **sources.md lists only free sources; paid or no-redistribution packs are listed under "Avoid, or local-only"**, because 1265 recommends no paid signups.
- [x] [DATA] Provenance? - decided **each sources.md row carries `R1028` (the 2026-10-28 research) or `bg` (background knowledge, unchecked)**, because only the first was researched; `bg` rows are leads and the license is re-read on the page every time.
- [x] [TOOLING] Script? - decided **none**, because the work is judgement plus web research; the living list is a markdown file the skill edits in place.
