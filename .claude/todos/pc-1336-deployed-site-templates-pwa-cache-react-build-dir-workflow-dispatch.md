<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Deployed-site templates: /pwa cache strategy, react.yml build dir, workflow_dispatch

**Type:** task
**Origin:** ai
**Summary:** Three skill templates that end up in deployed sites get their known defects fixed once Joe approves seeing the diffs.

## Why

Split out of pc-1283 on 2026-11-07: its doc and step-order fixes landed, but these three change files that ship into deployed sites, so the dev is shown the diff first (pc-1283's Approach said so, and the 2026-11-07 loop triage deferred them).

## Goal

The templates below work for returning users and for `/deploy`, with the dev having seen each diff.

## Context

- `skills/pwa/SKILL.md` Step 4 service worker is cache-first with a fixed `CACHE_NAME = "v1"`, so edited CSS/JS never reaches returning users. Step 6 now tells the dev to bump `v1` -> `v2` by hand; the template itself still has the defect. Options: network-first for HTML plus stale-while-revalidate for assets, or a cache name derived from a build stamp.
- `skills/update-workflow/templates/react.yml:82` uploads `build/` (Create React App). `skills/init-claude-md/SKILL.md:86` defines `react` as "Vite or CRA", and a Vite project outputs `dist/`. `skills/update-workflow/SKILL.md` Step 1 now routes `vite.config.*` projects to `vite.yml`, so the remaining choice is whether `init-claude-md` should stop calling Vite projects `react`.
- None of `html.yml`, `vite.yml`, `react.yml` has `workflow_dispatch`, which `skills/deploy/SKILL.md` requires. Adding it also needs `/update-workflow` to offer the diff to already-deployed repos (its Step 3 asks before overwriting a differing file).

## Approach

Draft each diff, show the dev, then edit. Do not touch a deployed site's workflow without the dev's yes.

## Acceptance

- A returning visitor gets edited CSS/JS after a redeploy without a manual cache bump.
- `react.yml`'s upload path matches what the project types `init-claude-md` assigns to `react` actually build.
- `/deploy` can fire a workflow synced from any of the three templates.
