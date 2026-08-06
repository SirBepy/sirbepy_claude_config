---
name: create-logo
description: Designs professional SVG logos end-to-end - brief, 6 distinct concepts in a self-contained HTML showcase, iteration, export and variants. Pure SVG, no external image APIs.
disable-model-invocation: true
argument-hint: "<brand/app name or brief>"
---

# /create-logo

> From brief to final mark: 6 genuinely different SVG concepts, shown side by side, iterated until one wins.

Synthesized from the best public logo skills (op7418/logo-generator-skill, neonwatty/logo-designer-skill, rknall/svg-logo-designer) plus Anthropic's canvas-design philosophy step. Pure SVG authoring - no Gemini/image-model dependency, no Python requirement.

## When to use

Manual trigger only, `/create-logo <brand or brief>`. For favicon *pipeline* work (generating the ico/png/manifest set from an existing mark), hand off to the `favicon` skill instead.

## Phase 1: Brief

1. **Auto-context first.** If run inside a project: read README/CLAUDE.md, existing icons/branding assets, and CSS/theme color variables. Extract name, purpose, personality, palette. Summarize what was found so no already-answered question gets asked.
2. **One batched question round** (AskUserQuestion, per global rules) covering ONLY what's still unknown:
   - **Format**: icon only / wordmark / combination mark (icon + text)
   - **Style direction**: minimal-geometric / organic-flowing / bold-corporate / playful / match existing app style
   - **Colors**: project colors / specific colors / monochrome / "surprise me"
   - "Just make something" -> defaults: icon only, minimal-geometric, monochrome `currentColor`.
3. **Design direction** (condensed canvas-design philosophy): before drawing, write 2-3 sentences naming the mood, the form language, and the one idea the mark should quietly express. Present it alongside the concepts, not as a separate approval gate.

## Phase 2: Concepts

Generate **6 distinct concepts**. Distinct means a different visual strategy, never parameter tweaks of one idea.

**Diversity allocation** (one each):
1. Pure geometric (clean shapes, no dots/lines)
2. Dot matrix (circle / rounded-rect / capsule / hexagon dots)
3. Line system (parallel lines, arcs, waves, spiral)
4. Mixed: dots + geometry (dots filling or forming a shape)
5. Mixed: lines + geometry (lines creating or accenting a form)
6. Node network, layered composition, or letter abstraction

Across the set, vary density, symmetry vs intentional asymmetry, and visual weight. Full pattern library with copy-paste SVG starters: `references/design-patterns.md` (read it before generating - its Part 0 principles are the quality bar).

**Hard quality rules** (from analysis of 100+ high-end marks):
- 1-2 core elements max, 5-6 total shapes max
- At least 40% of the canvas is negative space
- Primary stroke-width 2.5-4 (in a 0 0 100 100 viewBox); thin-line looks need dense repetition (6+ lines) for visual mass
- Single focal point; the eye must know where to look
- Negative-space cutouts get rounded openings, never sharp
- No gradients, shadows, or effects unless explicitly requested
- Must survive 16px. If a detail dies at 32px, simplify it now, not in review

**SVG conventions:**
- `viewBox="0 0 100 100"`, no fixed width/height; center around (50,50); 10-15 units edge padding
- Self-contained: no external fonts, images, or cross-file `<use>`
- Single-tone marks use `currentColor` (opacity tiers 0.3/0.6/1.0 for shading) so they recolor via CSS; fixed brand palettes use flat literal fills
- Meaningful group ids (`id="icon"`, `id="wordmark"`) kept stable across iterations
- Wordmark text: system fonts with generic fallback (`Helvetica, Arial, sans-serif`) or converted to paths
- Each concept gets a 1-line rationale tying the form to the product concept

**Generation:** write the SVGs inline (they are small). Fan out subagents only for a big batch request (5+ new directions at once), and then per global rules: `model: 'sonnet'`, full conventions + brief in every prompt, no commits.

## Phase 3: Showcase

Build ONE self-contained HTML file:
- **Inline every SVG** directly in the markup. Never `<img src="file.svg">` - the showcase must render from a `data:` URL (Claude Conductor's preview panel) where relative file refs are dead.
- Per concept card: the mark on a light swatch AND a dark swatch, label, rationale.
- **Favicon strip from round one**: each concept at 64/32/16px, so legibility problems surface immediately.
- Light/dark page toggle.

Show it: `/preview` when the Claude Conductor preview panel is reachable, otherwise write the file and open it in the browser. File location: the project's scratch convention (`.for_bepy/logos/` where that exists), else `logos/` in the project root.

## Phase 4: Iterate

- User narrows to 1-2 directions; apply targeted tweaks (resize, respace, recolor, combine elements from different concepts) directly.
- Number iterations, keep every version, regenerate the showcase each round with newest first. "Back to iteration N" makes N the new base.
- Keep group ids stable so feedback like "make the icon bigger" maps cleanly.
- Re-check the favicon strip every round; proactively thicken or delete whatever vanished at 32px.

## Phase 5: Deliver

- Final `logo.svg` written where the user wants it (default: the project's asset location if one exists, else `logos/`).
- **Layout variants only on request**: icon-only / horizontal lockup / stacked; monochrome-dark, monochrome-light, reversed.
- **PNG export on request**: standard sizes 16/32/48/192/512/1024/2048 via whichever converter is installed (resvg, Inkscape, ImageMagick, or cairosvg); say which was used. None installed -> say so and name the install options.
- **App/favicon integration**: use the `favicon` skill; replace only icon files the project already has, never add new ones it doesn't use.
- Usage guidelines doc (clear space, min sizes, do's/don'ts) only if a full brand package was asked for.
