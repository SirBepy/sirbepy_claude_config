---
name: bepy-project-setup-web
description: Web/HTML project standardization flow - runs favicon, PWA, GitHub Pages, deploy workflow and the setup guidelines in refs/web-project-setup.md. For Roblox/Luau projects use /bepy-project-setup-roblox instead.
disable-model-invocation: true
---

# /bepy-project-setup-web

> Standardize a new web project. The guidance (CLAUDE.md shape, widgets, styleguide, meta tags, README) lives in
> `~/.claude/refs/web-project-setup.md`; this skill runs it in order and calls the runnable skills between its steps.

## Flags

- `pick` (or free text like "let me pick" / "ask me what to skip") - ask one multi-select question of which steps to skip
  instead of running everything. Escape hatch for a project where a step must not run unattended (e.g. `/update-workflow`
  would overwrite a hand-tuned deploy.yml).
- Naming steps to skip ("skip favicon and readme") skips only those.

## Steps

Read `~/.claude/refs/web-project-setup.md` in full first. Run its "Step order" exactly, numbers 0-10, with these runnable skills at
their steps: `/favicon` (2), `/update-workflow` (3), `/github-pages-init` (4), `/portfolio-data` (7), `/pwa` (10). Steps 1, 5, 6, 8 and 9
(CLAUDE.md, widgets, styleguide, meta tags, README) are done by hand from the doc's sections; `/pretty-readme` output counts as
a finished README (section 9). The order is load-bearing, so never reorder.

Print `Running <step>...` and `Done <step>` around each, and do not stop between steps unless one needs input.

## Commit and summary

Run `/commit` with `CHORE: bepy project setup`. This flow never pushes. End with a one-line-per-step summary: ran / skipped by
request / skipped - nothing to do.
