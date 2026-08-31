---
name: mockup
description: Previews a UI idea visually before real implementation, reusing existing components where possible. Fires /brainstorm first if unexplored.
disable-model-invocation: true
argument-hint: "<what to preview>"
---

# /mockup

> See it before you build it, using real components where they exist.

## When to use

Manual trigger only, `/mockup <what to preview>`. Never auto-offered mid-`/brainstorm` or mid-implementation - the dev asks for this explicitly when they want to see a UI idea before it's built for real.

## Process

1. **Brainstorm gate.** Check whether THIS specific idea (not some unrelated thing earlier in the session) has already been brainstormed, including via a settled spec in `.claude/todos/` (backlog or `done/`) - `/brainstorm`'s own process checks there first. If not, run `/brainstorm` on it first - a mockup of an unexplored idea just previews the wrong thing faster.

   **Narrow exemption.** Skip `/brainstorm` only when ALL THREE hold: (a) the dev's own message already states the content requirements - what data or elements must appear; (b) every unresolved question is visual (layout, spacing, hierarchy, colour), which the mockup itself is the better instrument for answering; (c) no behavioral, architectural, or data question is entangled with the visual one. If any one fails, the gate stands. Disclosing the skip and naming the three conditions in the response is MANDATORY - an undisclosed skip is indistinguishable from the improvised override this exemption exists to replace.
2. **Pick the branch** based on the project:
   - **Web stack with an existing, running component library** → Real-component branch (step 3).
   - **Flutter/mobile, or a web project with nothing reusable yet (greenfield)** → Standalone-file branch (step 4).
3. **Real-component branch.** Build the preview as a scratch route/page inside the actual app, composed from the project's real existing components (real styles/CSS classes, real formatting/color/state helpers), not hand-rolled markup that merely imitates their look. The scratch route is a full preview PAGE per the Staging section below, not the bare component mounted alone in an empty root - the real component is what goes *inside* the stage, everything else in the Staging section is throwaway scaffolding around it. Bring it up via `/supervised-run`. Because the component itself is real, the dev may later keep/relocate it into the real implementation - that's not duplication - but the staging chrome (title, notes, stage container, sim controls) is preview-only and must never be promoted into the shipped route.
   - **Reused CSS is frequently scoped to an ancestor class** (e.g. a view's real styles only match under `.view-<name>`, not on the bare component class alone) - check the source CSS file for that ancestor selector and wrap the preview markup in it. Skipping this is the single easiest way to end up with the real classes silently matching nothing and the "real" preview rendering as unstyled div soup - worse than the standalone branch, and easy to miss if you never actually look at the render (see the mandatory verify step below). Don't blanket-copy the ancestor's OWN layout classes if they carry real-app-specific sizing (e.g. a `flex:1; overflow:hidden` meant for a fixed app shell) that would clip a taller scrolling preview page - take only the class needed for CSS selector scope, not any layout side effects that fight the preview's own shape.
   - Name every scratch file with a `mockup-` prefix (`mockup-<idea>.html/.ts/.css`, matching this skill's own name) so orphaned scratch routes are one `grep`/`Glob` away from being found and cleaned up.
4. **Standalone-file branch.** Build a single static HTML/CSS file using Tailwind CDN + Phosphor Icons CDN, following the Staging section below. Save it to `.for_bepy/mockups/` (gitignored scratch, same convention as `.for_bepy/screenshots/`; create the folder if missing). This file is visual-only and is NEVER copied into the real implementation - Flutter can't consume HTML, and greenfield has no real components yet to have used instead. Real implementation is always written clean afterward.
5. **Verify before showing the dev - actually look, don't assume the wiring worked.** Fetch/render the page and READ BACK a screenshot yourself before calling it ready. Confirm the real classes/CSS actually applied (a card should look like a card - bordered, backgrounded, padded - not bare unstyled text) and nothing silently failed to import/scope. A preview that compiles without error is not the same as a preview that rendered correctly - this is a distinct, non-skippable check from step 6's "capture a screenshot for the dev," which happens after this one passes, not instead of it.

   Three non-negotiable checks, each catching a different silent failure a screenshot glance misses:
   - **Gated selectors:** grep the reused stylesheet(s) for the selectors being copied, and for any gated/compound one (`.ancestor .foo`, `#some-id .foo`, a rule depending on a custom property defined elsewhere) either satisfy the gate in the preview markup/imports or note in the mockup's header comment what was hand-copied instead.
   - **Computed style, not a glance:** add an `evaluate` step reading `getComputedStyle(el)` (background/border/color, etc.) for at least one reused element and compare it against the stylesheet's actual rule - a component's children can look plausible while the parent's chrome silently failed to apply. The step's return value prints directly to the console as `evaluate: <value>` (JSON-stringified unless already a string, add a `label` field when a plan has several evaluates) - read it from there, no need to render it into the page and screenshot it.
   - **Geometric/numeric claims, measured:** if the mockup asserts square, centered, aligned, N px, same width, etc., add an `evaluate` step calling `getBoundingClientRect()` on the relevant element(s) and compare the actual numbers against the claim before stating it as fact - a screenshot is evidence the page rendered, not that the claimed property is true. When the claim is about overflow/scrolling, measure the element that actually scrolls, not just the outer wrapper - walk descendants for `scrollWidth > clientWidth + 2`, since an inner scroller (e.g. a table) can overflow while the card wrapping it reports no overflow at all.

   Use the shared `screenshot-helper.cjs` at `C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs` (same script `/screenshot` uses) to take the screenshot. Pass a bare filename as `out` (e.g. `mockup-<idea>.png`, no directory) and it auto-resolves into this session's `.for_bepy/screenshots/<pid>-<start-ticks>/` (throwaway verification shots, matching `/close`'s purge scheme) - no id to hand-build. If interaction the helper's `--plan` can't express forces a Playwright MCP capture instead, see `screenshot/SKILL.md`'s "Playwright MCP is not the capture path" section first - the MCP does not land in this folder on its own. Pick the mode per round, re-deciding each time rather than reusing the prior round's mode by habit:

   - No interaction needed, the page is correct on load - use `--url <url> --screenshot <out.png>` alone.
   - One click needed, and the selector's characters are all within `A-Za-z0-9_.:#[]=,-` and spaces - add `--click <selector>` to the same call.
   - The selector uses other characters (`>`, `~`, `+`, quotes, and similar), or the round needs more than one action - fall back to `--plan <plan.json>`, expressing each action as its own `{"type": ...}` step (`click`, `hover`, `selectOption`, `wait`, `scroll`, `waitForSelector`, `refresh`, `evaluate`, `screenshot`).
   - Step JSON shape per type: see `screenshot/SKILL.md`'s step-type table (same script, same types) for the full schema, including the `evaluate` IIFE requirement (`js` runs via `page.evaluate(step.js)` as code, not a function reference - it must be a self-invoking `(function(){...})()`, not a bare `() => {...}`).
   - Prefer `--plan` over `--click` even for an in-range selector if it contains a space: inside plan JSON the selector is just a string value with no shell-quoting risk, while a space in a constructed command line can silently split into extra argv tokens if quoting is dropped. If `--click` is used with a space-containing selector anyway, quote the whole selector in the constructed command (e.g. `--click ".foo .bar"`).
   - An animation or transition needs to settle before the shot - add `--wait <ms>` in screenshot mode, or a `{"type":"wait","ms":...}` step in plan mode.
   - Never combine `--click` or `--wait` with `--plan` in the same invocation - the script rejects that combination and tells you to move them into plan steps instead.

   When using `--plan`, write the plan JSON to `.for_bepy/mockup-step-<id>.json` where `<id>` is
   `close/rename-session.ps1 -GetId`'s output (`<pid>-<start-ticks>`, never a hand-rolled walk -
   see todo 60), start-ticks included because Windows recycles PIDs and a crashed session's stale
   file would otherwise be picked up as your own - a fixed shared name collides when two concurrent sessions in the same repo both run mockup rounds (Music Guesser session, 2026-08-01, found the file already owned by a concurrent favicon session). Reuse and overwrite this same per-session path every round; don't name a new file per round. Delete it once step 7's disposal decision fires, not after each round - step 7 owns this, not `/close`'s purge phase, which is scoped to `.for_bepy/screenshots/` only.
6. **Show it to the dev.**
   - **Standalone-file branch:** push it with `/preview <file>` so it auto-opens in Claude Conductor's in-app preview panel (Joe 2026-07-30, after verifying the panel's push-render path works: "i want all /mockup to always do /preview" - this re-reverses the 2026-07-24 browser-open default, which existed only because pushed previews used to silently never appear). If `/preview` reports Conductor unreachable (connection refused on 127.0.0.1:27182), follow its own fallback (open the file directly in the browser), then still capture a screenshot via `SendUserFile` so the dev has it in-chat too.
   - **Real-component branch:** unchanged - bring the scratch route up via `/supervised-run` (it's a live dev-server route, not a static file `/preview` can push), give the dev the URL, and capture a screenshot via `SendUserFile`.
7. **Dispose of every scratch artifact this run created, gated on whether a human was there to see it.** Once the dev has seen the preview, the skill's job is done - do not auto-continue into real implementation, that is a separate step the dev starts deliberately.

   **Signal: attended vs unattended.** Attended = an interactive session and the dev has responded/interacted since the preview went up. Unattended = running under `/autopilot`, or no dev response since the preview went up - the trigger this step used to key off ("once the dev is done looking") is unobservable here, so treat silence as unattended rather than firing immediately, the worst-case reading.

   - **Attended:** delete the real-component branch's scratch route/files (and stop any process started for them), and delete the standalone branch's `.for_bepy/mockups/<idea>.html` and plan-mode's `.for_bepy/mockup-step-<id>.json`, all automatically without asking, once the dev is done looking. This is `/mockup`'s own disposal - `/close`'s purge phase is scoped to `.for_bepy/screenshots/` only and does not own these paths. An orphaned scratch route with no disposal is the predictable failure mode (dead router entries, or an accidental commit) for the real-component branch's only advantage over the standalone branch, being real, keepable code.
   - **Unattended:** skip deletion entirely - the dev never got to look, and destroying the only interactive copy is worse than a leaked scratch file. Instead, file one `.claude/todos/` task (per `close/ai-todos-format.md`; Type: task, Origin: ai) listing every artifact path left behind (route files, or the `.for_bepy/mockups`/`mockup-step` paths), so it's tracked rather than either silently deleted or silently forgotten.

   Either case, one exception: if the dev has signalled they want to keep the real-component branch's code as the real implementation, confirm that explicitly before deleting - and it still owes this project's Testing & verification floor before being treated as done, "it's already real code" is not a free pass around that gate.

## Staging (applies to BOTH branches)

A preview is not just the component - it's the component made legible. Never ship a bare component floating alone in an unstyled page; that's unreadable and reads as a half-effort. Every preview page gets:

- **A title + one-sentence context blurb** at the top: what this is previewing and why, so the dev doesn't have to reconstruct context from a naked screenshot.
- **A padded "stage"**: the component sits inside a contrasting, bordered container with generous padding (not touching the viewport edges, not floating in a giant blank void). This is what makes a small card or control actually readable at a glance.
- **Labeled side-by-side sections when comparing options** (e.g. "V1" / "V2", or named variants) - each option gets its own full stage, generously sized, and rendered at its real target size, never scaled down to fit the board. That's the operative rule: an 8-variant board once drew "i cant see anything properly" because everything was shrunk to fit one screen, not because there were too many variants (see project memory on focused mockups). Absent a request for breadth, 2-3 options remains the soft default; iterate one direction at a time rather than dumping every idea in one crowded pass.
  - **Explicit-request exception:** if the dev asks for a specific count above 2-3, or for all the variants under discussion, honor it at true size, don't refuse or silently cap - state the count up front (e.g. "showing all 6 variants below"). Every option still gets its own clearly-labeled, generously-padded full card (title, one-line pitch, size ladder or relevant states); this mitigation is what makes a larger count legible (Hubbub favicon session, 2026-08-01: 12 concepts, each a full card, held up legible at 16px in a tab-strip check). If the full board no longer fits one viewport at true size, that's fine - capture it in sections instead of shrinking anything, via anchor ids plus URL fragments for a multi-shot screenshot (2026-07-29 session: 6 variants at true 390px width in a 3-across grid needed two screenshots, one per row, and every one stayed legible).
  - A per-variant one-line tradeoff caption under each stage is what makes a wide board actually usable - it lets the dev compare options without re-deriving each one's cost.
- **Live simulator controls for interactive/time-dependent states** (hover, urgent/error, empty, loading, countdown-style live values) - buttons/sliders that flip the actual rendered state live, rather than prose describing what it would look like, or a single static snapshot that hides the states that matter most (an urgency/escalation state is often the whole point of the preview).
- **A "Today" vs "Proposed" comparison when the mockup replaces or fixes existing shipped UI.** Render the CURRENT real component/markup (reuse the actual existing function/route, don't hand-describe it) side by side with the new one, both labeled. An improvement argued in the abstract is far weaker than one shown as a visible before/after - this is especially true for a bugfix-flavored redesign, where the "before" IS the bug.
- **A realistic-size stage in addition to the generously-padded one**, whenever the target surface has a fixed real-world container (a taskbar popup, a sidebar of known width, a phone viewport). The wide/spacious stage is for judging detail; a second stage clamped to the actual real width/height is for judging whether it still holds up cramped into where it will actually live. Skip this second stage only when the surface has no fixed constraint (e.g. a full responsive web page).
  - **Container queries versus viewport media queries - check before clamping.** Grep the component for `@container`/`@[...]` (container query) versus `sm:`/`md:`/`lg:` (viewport media query). A container query reads the stage's own width and fires correctly when clamped. A viewport media query reads the browser's actual viewport, so a 390px-wide stage sitting inside a wide browser window still evaluates against the wide viewport and silently renders the desktop branch - a layout the app never produces at that size. For a viewport-query breakpoint, resize the real browser viewport instead of the stage, and capture that as a separate shot explicitly labeled "real-viewport capture" so it isn't mistaken for the clamped stage.
  - A board mixing a clamped-width stage with a real-viewport capture must label which is which - an unlabeled fake-width stage next to a real one is worse than showing either alone.
- **A small "SCRATCH / PREVIEW ONLY" watermark or badge** rendered on the page itself (not just in the filename) - so a screenshot shared out of context (Slack, a later session) can't be mistaken for real shipped UI.
- A short closing note under each stage explaining the behavior/logic it demonstrates, when that isn't obvious from looking (e.g. what triggers a color or state change).

This staging scaffolding is intentionally the same regardless of which branch built the component - the dev's ability to *judge* the design shouldn't depend on which technical path was cheaper to reuse.

## Breaking a rejection loop (icon/logo rounds)

After 2 rounds of icon/logo concepts get rejected with no specific, actionable feedback (just "I
hate these" / "ugly", not "make X bigger" or "try blue instead"), stop generating another round
blind. Ask a diagnostic question card that splits the critique into execution / subject / palette
/ reference-style, so precise answers surface without the dev needing to already know what they
want - a reference-image ask or a tool switch is not the escalation, the question card is. Keep
the hand-coded SVG flow as the default for the first round or two; this is the escalation point,
not a ban on the technique. (Hubbub favicon session, 2026-08-01: a reference-image ask and an
AI-tool pivot both failed to break a 4-round rejection deadlock; the question card broke it in the
same session, using neither.)

When re-showing icon concepts after a rejected round, include the previously-rejected version as
an explicit labelled baseline alongside the new ones, not just new variants shown in isolation.
Also render a solid-black silhouette of each icon concept: a shape that reads at a glance in
silhouette is doing the actual work, color and detail can hide a weak base shape.

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
- Don't skip the brainstorm gate because the ask "sounds simple" - that judgment call is `/brainstorm`'s to make, not `/mockup`'s. Step 1's three-condition exemption is the ONLY sanctioned skip, and only when disclosed in the response.
- Don't skip the Staging section because the real-component branch felt like it should be "just render the real thing" - an under-staged real-component preview is worse than a well-staged standalone one; the dev is judging what they can see, not which branch produced it.
