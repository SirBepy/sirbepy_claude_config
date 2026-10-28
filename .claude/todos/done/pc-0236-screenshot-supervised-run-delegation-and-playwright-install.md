<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# screenshot: delegate server lifecycle to /supervised-run, resolve playwright via a stable named-reinstall path

**Type:** skill-improvement

## Goal

`skills/screenshot/SKILL.md` currently self-manages its dev-server lifecycle (hardcoded
ports, manual `run_in_background` start + poll + `npx kill-port` teardown) instead of
routing through `/supervised-run` like the rest of the codebase's long-lived-server
convention requires. It also resolves `playwright` via a content-hashed npx cache
directory, which `disk-doctor` correctly flags as safe-to-delete scratch - meaning a
routine disk cleanup can silently break this skill's next run. Fix both: delegate server
start/stop to `/supervised-run`, and pin playwright to a stable, explicitly-reinstallable
location.

## Context

`skills/screenshot/SKILL.md` (as of 2026-08-01):

**Server lifecycle (Step 2, lines 15-23 and Step 6, lines 82-86)** - self-managed:
```
## Step 2 - Detect and start the server

| Condition | Port | Command |
|---|---|---|
| `vite.config.*` exists | 5173 (or as configured) | `npm run dev` |
| React/Next in `package.json` | 3000 | `npm run dev` |
| `index.html`, no `package.json` | 8080 | `python -m http.server 8080` |

Start with `run_in_background: true`. Poll: `(Invoke-WebRequest -Uri "http://localhost:PORT" ...)` up to 15 tries, 1s apart.
...
## Step 6 - Stop the server

npx --yes kill-port PORT
```
This is exactly the pattern the global CLAUDE.md's "Process Hygiene" section and the
`/supervised-run` skill exist to replace: `/supervised-run`'s own description says "Use
when you need to start a LONG-LIVED dev server... Routes through server_supervisor for
visibility and no orphans." A hardcoded port table plus manual `kill-port` teardown is
exactly the orphan-risk pattern `/supervised-run` was built to eliminate (it also
"lists first - reuse before you create," which this skill's Step 2 doesn't do at all -
it always starts fresh, potentially colliding with an existing supervised entry for the
same project).

**Playwright resolution:** the screenshot helper (`C:/Users/tecno/.claude/skills/
screenshot/screenshot-helper.cjs`, referenced SKILL.md line 12 and Step 5 line 77)
resolves its `playwright` dependency via npx's content-hashed cache directory (under
`%LOCALAPPDATA%\npm-cache\_npx\<hash>\` or similar, exact path depends on how the script
requires/invokes it - confirm by reading `screenshot-helper.cjs`'s require/import
statements and any `package.json` next to it before implementing). `disk-doctor` treats
npx's `_npx` cache as safe-to-delete scratch (it's designed to be regenerated on demand),
so a routine disk cleanup can silently remove playwright's install out from under this
skill, breaking the NEXT `/screenshot` run with no warning until it fails.

## Approach

1. Read `skills/screenshot/SKILL.md` in full, and `screenshot-helper.cjs`'s dependency
   resolution (how it currently gets `playwright` - `require('playwright')`, a dynamic
   npx invocation, etc.) before editing either.
2. **Server delegation:** replace Step 2's self-managed start (hardcoded port table +
   `run_in_background` + polling) with an instruction to invoke `/supervised-run` for the
   detected dev-server command, following that skill's own "list first, reuse before you
   create" step so a `/screenshot` run doesn't spawn a duplicate server if one is already
   supervised for this project. Keep the project-type detection logic (vite/React-Next/
   plain-html) - only replace HOW the server gets started/stopped, not what command gets
   run. Use `/supervised-run`'s dynamic-port mechanism (`{PORT}` templating,
   `use_dynamic_port: true`) instead of the hardcoded 5173/3000/8080 table.
3. **Server teardown:** replace Step 6's `npx --yes kill-port PORT` with
   `/supervised-run`'s stop mechanism (`POST /procs/<id>/stop`) - or, if this skill
   should leave a reusable dev server running for the dev's later use rather than
   tearing it down every time (worth confirming - a screenshot run tearing down a
   server the dev was already using elsewhere would be a regression), change Step 6 to
   only stop the server if `/supervised-run` itself started a NEW entry this run (not if
   it reused an existing one). Resolve this behavioral question explicitly when picking
   up this todo rather than guessing silently.
4. **Playwright stability:** change `screenshot-helper.cjs`'s playwright resolution (or
   its package.json, if one exists alongside it) to use a stable, named install location
   instead of the npx content-hash cache - e.g. a proper `npm install playwright` inside
   `skills/screenshot/` with its own `package.json`/`node_modules` (excluded from git via
   `.gitignore` if not already), or an explicitly path-pinned global install. Add a named
   reinstall command (e.g. document `npm install` inside `skills/screenshot/` as the
   fix-it step) so a disk-doctor cleanup that removes it has an obvious, one-line
   recovery path instead of a confusing runtime failure.
5. Check whether `disk-doctor`'s scan logic (`skills/disk-doctor/windows.md` or similar)
   needs a corresponding note that `skills/screenshot/node_modules` (if that's the chosen
   fix) is NOT safe-to-delete scratch, unlike the npx cache it replaces.

## Acceptance

- `/screenshot` no longer hardcodes ports or manually manages `run_in_background`/
  `kill-port` - it delegates to `/supervised-run` for both start and stop.
- Playwright resolves from a stable location that survives an npx cache purge, with a
  documented one-command reinstall path.
- Run `/screenshot` end-to-end against a real project after the change to confirm both
  fixes work together (server comes up via the supervisor, screenshots are taken,
  cleanup behaves as decided in step 3 above).

## Notes

- Duplicate of 63 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
