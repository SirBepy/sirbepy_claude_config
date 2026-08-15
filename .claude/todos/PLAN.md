# Plan

**16 active todos.** The four long-parked ones below still stand. Updated 2026-08-15 after an
`/auto-do-todos` run took the backlog from 32 down to 10: 21 executed, 1 archived as churn.

Of the 16, **six carry an `## Open questions` block** written by that run and are waiting on Joe,
not on Claude: **326, 331, 333, 336, 337, 338**(shortcut). The next run opens with those. Six more
(**340-345**) were filed by the run itself from its own findings and have never been triaged, which
is what took the count back up to 16.

The old batch structure (16 batches, 71 todos, written 2026-08-11) is gone because the backlog it
described is gone. Now that the backlog is past a dozen again, re-run `/plan-todos` to rebuild
ordering rather than resurrecting the old headings from git.

Per the contract in `~/.claude/skills/close/ai-todos-format.md`, claim each todo in
`.claude/todos/.claims/` before executing it, and archive with `complete-todo.ps1` when done.

## Needs a session of its own (1)

- [ ] **58** - audit `skills/` and decide keep / update / remove per skill

Joe's own ask, and he deferred it on 2026-08-13 with "this is meant to be a whole session kind of
thing, so skip this for now". Do NOT open it as a side quest inside another run. Current scale is
**76 directories, 669 files, 664 tracked**, of which **12 are vendored** (the 11 Cloudflare-family
skills plus `impeccable`), documented in `skills/VENDORED.md`. Judge those 12 on "do we still want
this installed" rather than on quality, since their content is upstream's.

## Blocked on 58 (2)

Both add NEW skill surface, which is exactly what the audit might prune, so they wait.

- [ ] **11** - `/orphan-audit`, process forensics gets rewritten ad hoc every time
- [ ] **30** - `/story-shot`, the Storybook restart-wait-screenshot loop

Note **63** was in this group and is now done: Joe released it on 2026-08-13 because it extended an
existing skill instead of adding one, and it shared files with 295.

## Parked, do not build (1)

Not a checkbox on purpose. `/pickup` must never hand this to anyone as actionable.

- **95** - session activity log. Joe explicitly stopped the build 2026-07-30 and confirmed the park
  again on 2026-08-13. The file exists to preserve the research so it is not rediscovered.

## Resolved questions, kept so nobody re-asks

1. **Vendored skills.** The wholesale commit already happened in `4cc2977` (2026-08-12, 516 files),
   which was the option a `/rate-it` scored 4/10. `skills/VENDORED.md` was therefore written as
   documentation over the existing state. It found exactly ONE local patch in the whole vendored
   set, `skills/impeccable/reference/new-work.md`, verified by diffing against the vendoring commit.
   Narrowly still open: whether to `git rm --cached` the ~516 unpatched vendor files. Nobody has to;
   the silent-revert risk is one file wide.
2. **`hooks/` is tracked** as of `bcaa730`, 13 files, secret-scanned first. The absolute paths in
   `settings.json` stay on purpose: `${CLAUDE_PROJECT_DIR}` is real and documented, but it resolves
   to whichever project is open, and that file is the GLOBAL user-level settings whose hooks fire in
   every session, so a portable form would break everywhere except this repo.
3. **The corepack guard stays strict.** It governs WHICH binary installs, not what gets installed,
   and a global Yarn 1 once silently rewrote a Yarn 4 lockfile.

## Hook doctrine, learned the expensive way on 2026-08-13

Three detectors were spiked in one day and the pattern is now clear enough to save the next attempt:

- **Exact mechanical checks ship.** `hooks/em-dash-guard.py` is live because U+2014 is a codepoint.
- **Heuristic judgment calls do not.** The unverified-mechanism detector hit 67 percent false
  positives, the bare-question detector missed 20 to 25 percent of real cases against ~4025 real
  messages, and the command-chaining detector flagged 55 percent of 30047 real commands. All three
  are kept as `hooks/EXPERIMENTAL-*.py` with their measurements.

Measure against a real corpus BEFORE wiring anything, and prefer inverting the problem (require an
explicit marker on the legitimate case) over detecting the violation.
