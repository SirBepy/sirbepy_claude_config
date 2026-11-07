---
name: bepy-project-setup-web
description: Web/HTML project standardization flow - runs favicon, meta-tags, PWA, GitHub Pages, styleguide, deploy workflow, etc. For Roblox/Luau projects use /bepy-project-setup-roblox instead.
disable-model-invocation: true
---

# /bepy-project-setup-web

> Full web project standardization flow - runs all bepy web skills in order.

## Flags

- `pick` (or free text like "let me pick" / "ask me what to skip") - opt into the interactive
  picker instead of the default run-everything behavior.

## Step 0 - Git init

Before anything else:

1. If not already a git repo (`git status`), run `git init` with `main` as the
   initial branch.
2. If `.gitignore` is missing, create one with `.DS_Store`, `node_modules/`,
   `dist/`, `.env`.
3. If there are no commits yet and files exist to stage, run `/commit` with a
   `CHORE:` prefix for the initial commit.

## Step 1 - Determine what to skip

Run everything by default, no prompt - proceed straight to Step 2, unless the dev's invocation
text does one of these:

- Names specific step(s) to skip (e.g. "skip favicon and readme") - skip only those, run
  everything else, proceed to Step 2.
- Explicitly asks to pick/choose/be asked (`pick` flag, "let me pick", "ask me what to skip") -
  fall back to the interactive picker below. This is the escape hatch for a project where a step
  genuinely must not run unattended (e.g. `/update-workflow` would overwrite a hand-tuned
  deploy.yml the dev doesn't want templated).

**Interactive picker** (only when explicitly requested): use AskUserQuestion with multiSelect to
ask:

"Which skills do you want to SKIP? (Everything else will run)"

Options (listed in run order, see Step 2):
- "/init-claude-md" - Generate or update CLAUDE.md
- "/favicon" - Check and generate favicon svg + png + ico
- "/update-workflow" - Ensure deploy.yml matches the correct template
- "/github-pages-init" - Create the GitHub repo if missing and enable Pages
- "/inject-widgets" - Inject settings widget and animated background
- "/apply-styleguide" - Apply bepy styleguide and CSS vars
- "/portfolio-data" - Generate or update portfolio metadata (runs after styleguide so screenshots reflect final look)
- "/meta-tags" - Add missing meta tags to index.html
- "/readme" - Generate or update README.md
- "/pwa" - Add manifest.json + service worker

## Step 2 - Run skills in order

Run all non-skipped skills in exactly this order. The order is load-bearing: later steps read what
earlier ones produce.

1. `/init-claude-md` - later steps read `Type:` from CLAUDE.md.
2. `/favicon`
3. `/update-workflow` - `/github-pages-init` warns when `deploy.yml` is missing.
4. `/github-pages-init` - creates the GitHub repo when none exists. `/meta-tags` and `/readme`
   derive the Pages URL and badges from `git remote get-url origin`, so the remote has to exist
   before them.
5. `/inject-widgets`
6. `/apply-styleguide`
7. `/portfolio-data` - after the styleguide so its screenshots show the final look, and before
   `/meta-tags` and `/readme`, which read `.portfolio-data/metadata.json` and `PORTFOLIO.md`.
8. `/meta-tags`
9. `/readme`
10. `/pwa` - runs by default. Skip only if the dev's invocation text says not to (e.g. "skip pwa",
    "no pwa", "without PWA"), or the `pick` escape hatch was used and PWA was picked to skip.

For each one:

- Print `Running /skill-name...` before starting
- Run the full skill as defined in its SKILL.md
- Print `Done /skill-name` when complete
- Move to the next one

Do not stop between skills unless a skill requires user input. Handle the input and continue.

A `/pretty-readme` result is not part of this flow: `/readme` keeps an existing banner-style README
instead of rewriting it, see its Step 0.

## Step 3 - Commit

After everything is done, run `/commit`:

```
CHORE: bepy project setup
```

`/github-pages-init` ends by saying the push is left to the dev; this flow never pushes either.

## Step 4 - Summary

Print a summary of everything that ran:

```
Done. Here's what ran:

/init-claude-md     - created
/favicon            - generated svg + png + ico
/update-workflow    - already up to date, skipped
/github-pages-init  - repo created, Pages enabled
/inject-widgets     - injected both scripts
/apply-styleguide   - replaced 14 hardcoded values, applied .card to 3 elements
/portfolio-data     - updated, screenshots taken
/meta-tags          - added og:title, og:description, og:image
/readme             - generated
/pwa                - manifest + service worker created
```

## Notes

- Commit at the end via /commit (Step 3).
- If a skill is skipped by request (named skip or interactive picker), note it as "skipped by request" in the summary.
- If a skill has nothing to do, note it as "skipped - nothing to do" in the summary.
