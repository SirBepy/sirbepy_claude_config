<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# settings.local.json is versioned nowhere, so its hook wiring is one disk failure from gone

**Type:** task
**Origin:** ai

## Goal

Decide and implement whether `settings.local.json`'s contents should be recoverable, rather than
existing only on this machine by accident.

## Context

Found 2026-08-19 during a full inventory sweep of `~/.claude`.

`.gitignore` is deny-all-then-allowlist and excepts `!settings.json`, but NOT `settings.local.json`.
So `settings.local.json` is untracked and unbacked-up, while it currently carries real config:

- the impeccable design-detector hook wiring (`PostToolUse` and `Stop` entries)
- extra permission allows

That means the design-detector hook exists nowhere but this disk. Reinstalling on a new machine, or
losing the file, silently drops the hook with no error and no diff - the exact silent-desync failure
mode the memory-index rule already warns about in another context.

Two legitimate answers, and this todo is to pick one deliberately rather than leave it accidental:

1. **It should be machine-local.** Then that is fine, but the file should say so at the top, and the
   design-detector wiring probably belongs in the tracked `settings.json` instead, since there is
   nothing machine-specific about it.
2. **It should be tracked.** Then add an allowlist exception, after auditing the file for anything
   secret (permission allows are not secrets; tokens would be).

## Approach

1. Read `settings.local.json` in full. Classify every key: genuinely machine-specific (paths, PIDs,
   per-machine toggles) vs portable config that only landed here by accident.
2. Audit for secrets before considering tracking it. Run `skills/commit/secret-scan.sh` against it.
   If anything sensitive is present, option 2 is off the table for the whole file and the portable
   keys move to `settings.json` instead.
3. Implement the chosen option:
   - Portable keys (the impeccable hook wiring especially) move into the tracked `settings.json`.
   - If a genuinely machine-local remainder exists, leave it in `settings.local.json` and add a
     leading comment saying it is intentionally untracked and why.
4. Verify the hooks still fire after the move. A settings edit that silently unwires a hook is the
   main risk here.

## Acceptance

- Every key in `settings.local.json` is either tracked in `settings.json` or documented as
  deliberately machine-local.
- The impeccable design-detector hook is provably still wired after the change: show the
  `settings.json` entry and a real trigger, not a claim.
- `secret-scan.sh` is clean on anything newly tracked.
- `git status` shows no unexpected new tracked files beyond the intended one.

## Notes

Do not blanket-add `!settings.local.json` to `.gitignore` without step 2. The allowlist pattern is
the right pattern here and the reason it is safe is that additions get audited first.
