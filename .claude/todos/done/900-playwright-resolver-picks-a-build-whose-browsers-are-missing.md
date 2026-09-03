<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the two guard hits are both in done/ and are different surfaces. 236 is the screenshot skill's own server/playwright plumbing. 288 is the one that BUILT this resolver's newest-match scan to replace a hash-pinned path - this todo is the next defect in that scan, not a repeat of it. -->
# playwright-resolve.cjs picks the newest npx-cache build without checking its browsers exist

**Type:** task
**Origin:** ai

## Goal

Stop `getChromium()` from handing back a Playwright build whose browser binaries were never
downloaded. Today it silently breaks every browser-driving script on the machine, in every repo, at
the moment some unrelated command refreshes the npx cache.

## Context

Hit live on 2026-09-03 during an `/auto-do-todos` run in `C:\Users\tecno\Desktop\Projects\countoff`.
Cost roughly 20 minutes of misdiagnosis plus a 115 MB download to recover, and it read as a project
bug for the first several minutes.

`~/.claude-personal/skills/_shared/playwright-resolve.cjs` resolves chromium as: normal `require`
first, then `findInNpxCache()`, which scans `%LOCALAPPDATA%/npm-cache/_npx/*/node_modules/playwright`
and returns the entry with the **newest mtime**:

```js
.map(p => ({ p, mtime: fs.statSync(p).mtimeMs }))
.sort((a, b) => b.mtime - a.mtime);
return hits.length ? hits[0].p : null;
```

Newest-mtime is not the same as usable. The existing `package.json` check proves the PACKAGE is
there; it says nothing about whether that build's browser revision was ever downloaded into
`%LOCALAPPDATA%/ms-playwright`.

What happened concretely:

- A probe ran fine (`verify/menu-probe.cjs` in countoff, 12/12) against a working cached build.
- Something then materialised a newer entry, `playwright@1.63.0-alpha-2026-08-31`, in the npx cache.
  In this instance it was a plain `npx --yes playwright install chromium`, which REFUSED to install
  (the target repo has no playwright dependency, so npx printed its "install @playwright/test first"
  banner) but still left a fresh, browser-less cache entry behind.
- Every subsequent script died with
  `browserType.launch: Executable doesn't exist at ...\chromium_headless_shell-1243\...`.
  `ms-playwright` held revisions 1208, 1228 and 1234; the newly-selected build wanted 1243.
- The failure surfaces at `launch()` inside whatever script is running, so it reads as that script's
  bug. Two different probes in two different states breaking at once with no code change between
  them is the only real tell.

The resolver's own error text points at `npx --yes playwright install chromium`, which is exactly
the command that CAUSED this, and which cannot fix it from inside a repo that has no playwright
dependency. The fix that worked was running the selected build's own CLI directly:

```
node "<npx-cache>/<hash>/node_modules/playwright/cli.js" install chromium
```

## Approach

- In `findInNpxCache()`, do not return a candidate on mtime alone. Walk the sorted list and return
  the first entry that is actually launchable, e.g. by resolving its expected browser revision
  (`<pkg>/browsers.json`, or `chromium.executablePath()` inside a `try`) and confirming that path
  exists under `%LOCALAPPDATA%/ms-playwright`. Fall through to the next candidate otherwise. That
  alone turns this from a hard break into a self-healing preference for the newest WORKING build.
- If no candidate is launchable, throw a message naming the real fix - the `cli.js install chromium`
  form above with the resolved path interpolated - rather than the `npx --yes playwright install
  chromium` line, which is actively misleading in the situation that produces this error.
- Have the throw name the missing revision and the revisions that ARE present. That one line would
  have made this diagnosable in seconds.

## Acceptance

- With a browser-less newer build present in the npx cache alongside a working older one,
  `getChromium()` returns the working one and a probe still passes.
- With NO launchable build present, the thrown message names the specific `cli.js install` command
  for the build it selected, and that command, pasted verbatim, fixes it.
- The existing happy path (a single good cached build) is unchanged.

## Notes

Do not "fix" this by pinning a hash. `findInNpxCache` was written precisely because a hardcoded
npx-cache hash path vanishes on cache eviction or a version bump - see todo 295, and todo 288 in
`done/`, which shipped this newest-match scan on 2026-08-13 as the replacement for exactly that.
This todo is the next defect in that scan, not an argument against it: 288 fixed "the pinned path
disappears", and left open "the path we pick might not work". The bug is the missing liveness check.

Filed from a countoff session rather than that repo's backlog, because the resolver is shared global
tooling under `~/.claude-personal/skills/_shared/` and this breaks every project that uses it.
- Completed in /mega-todos wave 1, commit 37d036d: findInNpxCache now walks sorted candidates and returns the first whose chromium binary genuinely exists, throwing a precise install command when none do.
