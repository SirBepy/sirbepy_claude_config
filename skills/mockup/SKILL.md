---
name: mockup
description: Triggers on /mockup only. Previews a UI idea visually before real implementation, reusing existing components where possible. Fires /brainstorm first if unexplored.
argument-hint: "<what to preview>"
---

# /mockup

> See it before you build it, using real components where they exist.

## When to use

Manual trigger only, `/mockup <what to preview>`. Never auto-offered mid-`/brainstorm` or mid-implementation - the dev asks for this explicitly when they want to see a UI idea before it's built for real.

## Process

1. **Brainstorm gate.** Check whether THIS specific idea (not some unrelated thing earlier in the session) has already been brainstormed. If not, run `/brainstorm` on it first - a mockup of an unexplored idea just previews the wrong thing faster.
2. **Pick the branch** based on the project:
   - **Web stack with an existing, running component library** → Real-component branch (step 3).
   - **Flutter/mobile, or a web project with nothing reusable yet (greenfield)** → Standalone-file branch (step 4).
3. **Real-component branch.** Build the preview as a scratch route/page inside the actual app, composed from the project's real existing components (real styles/CSS classes, real formatting/color/state helpers), not hand-rolled markup that merely imitates their look. The scratch route is a full preview PAGE per the Staging section below, not the bare component mounted alone in an empty root - the real component is what goes *inside* the stage, everything else in the Staging section is throwaway scaffolding around it. Bring it up via `/supervised-run`. Because the component itself is real, the dev may later keep/relocate it into the real implementation - that's not duplication - but the staging chrome (title, notes, stage container, sim controls) is preview-only and must never be promoted into the shipped route.
   - **Reused CSS is frequently scoped to an ancestor class** (e.g. a view's real styles only match under `.view-<name>`, not on the bare component class alone) - check the source CSS file for that ancestor selector and wrap the preview markup in it. Skipping this is the single easiest way to end up with the real classes silently matching nothing and the "real" preview rendering as unstyled div soup - worse than the standalone branch, and easy to miss if you never actually look at the render (see the mandatory verify step below). Don't blanket-copy the ancestor's OWN layout classes if they carry real-app-specific sizing (e.g. a `flex:1; overflow:hidden` meant for a fixed app shell) that would clip a taller scrolling preview page - take only the class needed for CSS selector scope, not any layout side effects that fight the preview's own shape.
   - Name every scratch file with a `mockup-` prefix (`mockup-<idea>.html/.ts/.css`, matching this skill's own name) so orphaned scratch routes are one `grep`/`Glob` away from being found and cleaned up.
4. **Standalone-file branch.** Build a single static HTML/CSS file using Tailwind CDN + Phosphor Icons CDN, following the Staging section below. Save it to `.for_bepy/mockups/` (gitignored scratch, same convention as `.for_bepy/screenshots/`; create the folder if missing). This file is visual-only and is NEVER copied into the real implementation - Flutter can't consume HTML, and greenfield has no real components yet to have used instead. Real implementation is always written clean afterward.
5. **Verify before showing the dev - actually look, don't assume the wiring worked.** Fetch/render the page and READ BACK a screenshot yourself before calling it ready. Confirm the real classes/CSS actually applied (a card should look like a card - bordered, backgrounded, padded - not bare unstyled text) and nothing silently failed to import/scope. A preview that compiles without error is not the same as a preview that rendered correctly - this is a distinct, non-skippable check from step 6's "capture a screenshot for the dev," which happens after this one passes, not instead of it.

   Use the shared `screenshot-helper.cjs` at `C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs` (same script `/screenshot` uses) to take the screenshot. Pick the mode per round, re-deciding each time rather than reusing the prior round's mode by habit:

   - No interaction needed, the page is correct on load - use `--url <url> --screenshot <out.png>` alone.
   - One click needed, and the selector's characters are all within `A-Za-z0-9_.:#[]=,-` and spaces - add `--click <selector>` to the same call.
   - The selector uses other characters (`>`, `~`, `+`, quotes, and similar), or the round needs more than one action - fall back to `--plan <plan.json>`, expressing each action as its own `{"type": ...}` step (`click`, `wait`, `scroll`, `waitForSelector`, `refresh`, `evaluate`, `screenshot`).
   - Prefer `--plan` over `--click` even for an in-range selector if it contains a space: inside plan JSON the selector is just a string value with no shell-quoting risk, while a space in a constructed command line can silently split into extra argv tokens if quoting is dropped. If `--click` is used with a space-containing selector anyway, quote the whole selector in the constructed command (e.g. `--click ".foo .bar"`).
   - An animation or transition needs to settle before the shot - add `--wait <ms>` in screenshot mode, or a `{"type":"wait","ms":...}` step in plan mode.
   - Never combine `--click` or `--wait` with `--plan` in the same invocation - the script rejects that combination and tells you to move them into plan steps instead.

   When using `--plan`, write the plan JSON to the fixed path `.for_bepy/mockup-step.json`. Reuse and overwrite this same path every round of a session instead of naming a new file per round. Delete it once, at session end, alongside the rest of the `.for_bepy` scratch cleanup, not after each round.
6. **Show it to the dev.**
   - **Standalone-file branch:** push it with `/preview <file>` so it auto-opens in Claude Conductor's in-app preview panel (no browser tab, no localhost server - this replaced the old flow, Joe 2026-07-20: "I never wanted to have to manually choose to see the html here... by default you should open it up and show it"). If `/preview` reports Conductor isn't reachable (connection refused on 127.0.0.1:27182), it already falls back to opening the file directly per its own skill - follow that fallback, then still capture a screenshot via `SendUserFile` so the dev has it in-chat too.
   - **Real-component branch:** unchanged - bring the scratch route up via `/supervised-run` (it's a live dev-server route, not a static file `/preview` can push), give the dev the URL, and capture a screenshot via `SendUserFile`.
7. **Stop, and dispose of the real-component branch's scratch route unless told to keep it.** Once the dev has seen the preview, the skill's job is done - do not auto-continue into real implementation, that is a separate step the dev starts deliberately. For the real-component branch specifically: ask whether to delete the scratch route/files and stop any process you started for them, or leave them running/in place for further iteration. Default to deleting once the dev confirms they're done looking - an orphaned scratch route with no disposal step is the predictable failure mode (dead entries in a router, or an accidental commit) for a mechanism whose only advantage over the standalone branch is that it's made of real, keepable code. If the dev DOES want to keep it as real implementation, it still owes this project's Testing & verification floor before being treated as done - "it's already real code" is not a free pass around that gate.

## Staging (applies to BOTH branches)

A preview is not just the component - it's the component made legible. Never ship a bare component floating alone in an unstyled page; that's unreadable and reads as a half-effort. Every preview page gets:

- **A title + one-sentence context blurb** at the top: what this is previewing and why, so the dev doesn't have to reconstruct context from a naked screenshot.
- **A padded "stage"**: the component sits inside a contrasting, bordered container with generous padding (not touching the viewport edges, not floating in a giant blank void). This is what makes a small card or control actually readable at a glance.
- **Labeled side-by-side sections when comparing options** (e.g. "V1" / "V2", or named variants) - each option gets its own full stage, generously sized. Cap it at 2-3 options shown at once; a dense multi-variant grid shrinks everything below legibility (a past incident with an 8-variant board drew "i cant see anything properly" - see project memory on focused mockups). Iterate one direction at a time rather than dumping every idea in one crowded pass.
- **Live simulator controls for interactive/time-dependent states** (hover, urgent/error, empty, loading, countdown-style live values) - buttons/sliders that flip the actual rendered state live, rather than prose describing what it would look like, or a single static snapshot that hides the states that matter most (an urgency/escalation state is often the whole point of the preview).
- **A "Today" vs "Proposed" comparison when the mockup replaces or fixes existing shipped UI.** Render the CURRENT real component/markup (reuse the actual existing function/route, don't hand-describe it) side by side with the new one, both labeled. An improvement argued in the abstract is far weaker than one shown as a visible before/after - this is especially true for a bugfix-flavored redesign, where the "before" IS the bug.
- **A realistic-size stage in addition to the generously-padded one**, whenever the target surface has a fixed real-world container (a taskbar popup, a sidebar of known width, a phone viewport). The wide/spacious stage is for judging detail; a second stage clamped to the actual real width/height is for judging whether it still holds up cramped into where it will actually live. Skip this second stage only when the surface has no fixed constraint (e.g. a full responsive web page).
- **A small "SCRATCH / PREVIEW ONLY" watermark or badge** rendered on the page itself (not just in the filename) - so a screenshot shared out of context (Slack, a later session) can't be mistaken for real shipped UI.
- A short closing note under each stage explaining the behavior/logic it demonstrates, when that isn't obvious from looking (e.g. what triggers a color or state change).

This staging scaffolding is intentionally the same regardless of which branch built the component - the dev's ability to *judge* the design shouldn't depend on which technical path was cheaper to reuse.

## Dark-mode / forced-theme extension guard

Preview pages are frequently already dark-themed by design (matching the target app), and a browser dark-mode extension re-processing an already-dark page mangles the colors the dev is trying to judge. Every preview page's `<head>` gets:

```html
<meta name="color-scheme" content="dark">
<meta name="darkreader-lock">
```

`darkreader-lock` is Dark Reader's own documented opt-out (the extension checks for this exact meta tag and skips processing the page entirely - source: darkreader/darkreader GitHub). `color-scheme` is the general browser signal (native form controls/scrollbars render dark, and some other forced-dark implementations respect it too) - include both, since the dev may run a different extension than Dark Reader. If the dev names a specific different plugin, verify its actual opt-out mechanism instead of assuming this one covers it.

## Rules

- No dedicated `mockup-style.md` convention file. When real components exist, the existing codebase already IS the style reference. When falling back to the standalone file, Tailwind CDN + Phosphor Icons is the default - no extra file needed for that either.
- Never wire a standalone-file mockup into real implementation code, even if it looked exactly right - rebuild it clean.
- Don't skip the brainstorm gate because the ask "sounds simple" - that judgment call is `/brainstorm`'s to make, not `/mockup`'s.
- Don't skip the Staging section because the real-component branch felt like it should be "just render the real thing" - an under-staged real-component preview is worse than a well-staged standalone one; the dev is judging what they can see, not which branch produced it.
