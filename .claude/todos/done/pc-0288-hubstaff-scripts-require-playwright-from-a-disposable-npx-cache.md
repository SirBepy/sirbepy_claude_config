<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The two HubStaff scripts require playwright from a hash-keyed npx cache that can vanish

**Type:** task
**Origin:** ai

## Goal

Make `skills/clockify-reconciliator/scripts/hs_preflight.cjs` and `hs_weekshot.cjs` resolve
playwright in a way that survives an npx cache clean or a playwright version bump, and factor out
the boilerplate they duplicate.

## Context

Found by `/code-check` during `/close` on 2026-08-12, over commit `8d83c75`.

Both scripts open with the same line:

    const { chromium } = require('C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');

`hs_preflight.cjs:4` and `hs_weekshot.cjs:4`. That path points into npm's `_npx` cache, and
`e41f203b7505f1fb` is a content hash of the package set npx resolved at the time. The directory
exists right now (verified), but there are 29 sibling hash directories under `_npx`, and that whole
tree is disposable: `npm cache clean`, an npx eviction, or a playwright version change produces a
different hash and leaves these scripts throwing module-not-found.

This matters more than a normal broken-path risk because of what these scripts are FOR. They were
written for todo 100 specifically to remove the skill's dependency on a Playwright MCP server being
connected, after a 2026-08-01 run broke when it was not. A silently-evaporating require path
reintroduces the same class of failure the todo existed to eliminate, just with a different trigger.

Secondary, same two files: the CLI arg parser (`get()`), the `--org`/`--user`/`--profile` extraction,
the usage-error exit, and the `launchPersistentContext` setup are duplicated verbatim across both.
About 15 lines each way, in a matched pair of files shipped together.

## Approach

For the require path, decide between these and say why in the commit:

1. Add a real `package.json` beside the scripts with playwright as a dependency, and a documented
   one-time `npm install` in the skill. Most conventional, adds a `node_modules` under the skill.
2. Resolve at runtime: try `require('playwright')` first, fall back to scanning `_npx/*/node_modules`
   for the newest match, and fail with an actionable message naming the install command. No install
   step, but more moving parts.
3. Keep the pinned path but add an existence check at startup that fails loudly with the exact
   `npx playwright` command to re-materialize it. Cheapest, still breaks, but breaks legibly.

Option 2 or 3 keeps the zero-install property the scripts were written for; option 1 is the one that
actually stops the problem recurring. Whichever is picked, the failure message must name the fix.

Then extract the shared CLI parsing and browser launch into a `scripts/hs_common.cjs` both require,
so the resolution strategy is written once rather than twice.

## Acceptance

- Neither script contains a hardcoded `_npx` hash path.
- With playwright unavailable, both scripts exit with a message naming the exact command to fix it,
  rather than a raw module-not-found stack.
- The arg parser and browser launch exist in one file, not two.
- `node --check` passes on every touched file.

## Notes

- The `--out-dir` default of `C:/Users/tecno/Desktop` in `hs_weekshot.cjs:15` is deliberate (the
  weekly screenshots are a deliverable Joe looks at, not throwaway verification output) and is NOT
  part of this todo.
- Neither script has been run against the live HubStaff site yet, per todo 100's own closing note.
- Done 2026-08-13. New hs_common.cjs holds getChromium() (normal require first, then a scan of _npx/*/node_modules/playwright for the newest match, then an actionable throw naming the two fix commands) plus the shared getArg() and launchProfileContext(). Both hubstaff scripts now require it; no hash-pinned _npx path remains in either. Verified live: normal require genuinely fails from that dir, the fallback resolves a working chromium, and with the cache hidden the actionable message fires. Left open: screenshot-helper.cjs has the identical bug, filed as todo 293.
