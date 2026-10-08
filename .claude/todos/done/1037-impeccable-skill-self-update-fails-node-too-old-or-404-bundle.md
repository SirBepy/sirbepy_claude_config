<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=5, reconfirm-count=3, content-hash=1d2b35f4 -->
<!-- duplicate-checked: 327 is a Shortcut search skill gap, 489 is a mega-todos verify-reachability bug, 889 is a Flutter/zng-app build clobber - none are about impeccable's own self-update; the guard only matched on generic "skill/update/verify/bundle" vocabulary -->
# impeccable skill self-update fails (Node too old and/or a 404 bundle-verify)

**Type:** task
**Origin:** dev

## Goal

Get the `impeccable` skill updated from the currently-installed v4.0.4 to the latest (v4.4.0 as of
2026-09-28), or determine definitively that it can't be until Node is upgraded, and act on that.

## Context

Joe asked for the update twice this session (2026-09-28). Three attempts total:

1. `npx impeccable update` - `Download failed: invalid zip data` (x2, identical both times).
2. After `npx --yes clear-npx-cache` and retrying with `npx --yes impeccable@latest update` -
   different failure this time: an `npm warn EBADENGINE` for `impeccable@4.1.0` requiring
   `node >=22.18.0` while this machine runs `node v22.13.0`, immediately followed by
   `Download failed: Could not verify skill bundle: HTTP 404. Nothing was installed; retry or
   update the CLI. If this persists, report it at
   https://github.com/pbakaus/impeccable/issues/479`.

The engine warning and the switch from "invalid zip" to "HTTP 404" on the same retry strongly
suggests the Node version mismatch is the real blocker - an old Node may be causing `npx` to
resolve/fetch a bundle URL or manifest incorrectly. Not confirmed as root cause, just the most
likely one given the timing.

Deliberately NOT acted on further this session: bumping the machine's global Node version is a
toolchain change outside the scope of "update one skill," and doing it silently without asking
would be an overreach.

## Approach

1. Check current Node version and available upgrade paths (`nvm`/`fnm`/`nvs` if installed, or a
   direct Node installer) - ask Joe before actually changing anything, since this affects every
   Node-based tool on the machine, not just this skill.
2. If Joe approves a Node bump: bump to >=22.18.0, then retry `npx impeccable update` clean.
3. If Joe does NOT want to bump Node yet: check whether GitHub issue #479 (linked in the error) has
   a known workaround or fix that doesn't require the Node bump, and report back rather than retry
   blindly a 4th time.

## Acceptance

- `impeccable` skill reports as updated to the latest version, OR
- A clear, confirmed reason is recorded for why it can't be updated on this machine right now
  (e.g. "blocked on Node upgrade, Joe deferred it").

## Notes

- Phase 0 answer (Joe): bump Node now to >= 22.18.0, re-run `npx impeccable update`, then re-trim the description for the listing budget. (2026-10-07, /loop-todos Phase 0)

Do not retry `npx impeccable update` a 4th time without a state change first (Node bump, or a
fix from issue #479) - three attempts with two different failure signatures is enough to call this
non-transient.
- 2026-10-06 (loop-todos cycle 2): todo 984 trimmed impeccable's description to fit the listing budget and removed it from `LEGACY_OVER_BUDGET_DEBT` in ci/check_skill_frontmatter.py. A successful `npx impeccable update` would restore the upstream ~895-char description and turn CI red; re-trim the description after any update.
- Completed 2026-10-08 (loop-todos cycle 1, Joe approved the bump 2026-10-07): nvm-windows Node 22.13.0 -> 22.23.3 (globals were only npm/corepack, nothing to reinstall); npx impeccable@4.1.0 update succeeded, skill now v4.5.0 plus engine binary v0.1.11 (Authenticode-signed by Renaissance Geek, Inc.), 4 agents in agents/, and its hooks rewritten into the gitignored settings.local.json. Description re-trimmed to the listing budget; the 17 MB bin/ dir is gitignored. The two old settings.json impeccable hook entries point at the now-deleted scripts/hook.mjs and no-op.
