<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# /pwa skill needs a bail-out for bundler-based projects, like its existing Tauri check

**Type:** skill-improvement

## Goal

Add a Step-0-style check to the personal `/pwa` skill (`~/.claude-personal/skills/pwa/SKILL.md`)
that detects a bundler/framework project with its own PWA plugin ecosystem (Vite + React,
Next.js, etc.) and defers to that ecosystem's tooling instead of hand-rolling a `manifest.json` +
`sw.js` from its static-site template.

## Context

2026-08-03, `frontend2/pwa-standalone-shell` session: `/pwa` was invoked on `frontend2/`, a Vite +
React + TypeScript app inside the Fibo monorepo. The skill's actual steps assume a plain static
site (`assets/images/favicon.png`, `.portfolio-data/metadata.json`, hand-written `sw.js` with a
literal `ASSETS` array of relative paths) — none of which exist in a Vite project, and the
generated manifest/SW shape would have conflicted with `frontend2`'s real setup (no `public/`
convention match, no Vite asset-hashing awareness, and critically: the sibling package `frontend/`
already solves this exact problem via `vite-plugin-pwa`, the correct idiomatic tool for a Vite
app). The skill was abandoned mid-run and the PWA setup was done by hand instead, mirroring
`frontend/vite.config.ts`'s existing `VitePWA(...)` config.

The skill already has exactly this kind of bail-out for Tauri (`Step 0 - Skip for Tauri / desktop
projects`: checks for `src-tauri/` or `CLAUDE.md`'s `Type: tauri`, prints a skip message, stops).
The same pattern needs a sibling for bundler-based web projects.

## Approach

Add a `Step 0b` (or extend Step 0) that checks for `vite.config.ts`/`vite.config.js`,
`next.config.*`, or an equivalent bundler config in the project root before proceeding to Step 1's
"already done" check. If found:
- Print a message naming the idiomatic tool for that stack (`vite-plugin-pwa` for Vite,
  `next-pwa`/`@ducanh2912/next-pwa` for Next.js, etc.) instead of generating a hand-rolled
  `manifest.json` + `sw.js`.
- If a sibling package in the same repo already has a working PWA setup (check for
  `vite-plugin-pwa` in a sibling `package.json`), suggest mirroring that exact config rather than
  starting from scratch — the correct answer is very often "copy the sibling's config", not "write
  a fresh one from the skill's static-site template".
- Otherwise, stop and let the invoking session set it up manually (or hand off to a more capable
  skill), same as the Tauri bail-out does.

## Acceptance

- Running `/pwa` inside a Vite or Next.js project no longer generates a static-site-shaped
  `manifest.json`/`sw.js` pair — it either bails with a pointer to the right tool, or (stretch)
  actually wires up `vite-plugin-pwa`/`next-pwa` correctly.
- The existing Tauri bail-out behavior is unchanged.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 202; renumbered to 41 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: added `Step 0b - Skip for bundler-based projects` to `skills/pwa/SKILL.md:20-43`, mirroring Step 0's shape - detects Vite/Next config, checks sibling packages for an existing `vite-plugin-pwa`/`next-pwa` setup to mirror, else points at the idiomatic tool and stops. Tauri bail-out untouched.
