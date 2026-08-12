<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=1, content-hash=21d83eca -->
# `.claude/todos/` is untracked in the ~/.claude repo, so 85 todos have zero backup

**Type:** task
**Origin:** ai

## Goal

Decide whether `~/.claude`'s own todos backlog should be tracked in git, and act on the decision.
Right now it is not, and nothing else backs it up.

## Context

`C:\Users\tecno\.claude\.gitignore` is an allowlist: it starts with `*` and then re-includes
specific paths (`!skills/`, `!refs/`, `!snippets/`, `!commands/`, `!agents/`, `!context/`,
`!code-style/`, `CLAUDE.md`, `settings.json`). `.claude/todos/` is not on that list, so
`git ls-files .claude/todos/` returns 0 files.

Every other project's backlog inherits its repo's tracking. This one, the backlog that holds all the
global-tooling work, is the single unbacked-up copy.

Concrete exposure, 2026-08-12: a `/cleanup-todos` marker run rewrote 90 files in place. A bug in the
marker script (unanchored regex plus `String.Replace`, which swaps every occurrence rather than the
matched one) overwrote a quoted evidence block inside todo `99`'s prose. It was only recoverable
because that run happened to take an ad-hoc zip snapshot to `C:\tmp` first. With no snapshot and no
git history there would have been no way to know what the original line said.

The backlog is also the source of truth `/mega-todos` and `/auto-do-todos` read from, so corruption
there silently mis-steers every later run.

## Approach

The decision is which of these, not whether to do something:

1. **Track it** - add `!.claude/`, `!.claude/todos/`, `!.claude/todos/**` to `.gitignore`. Full
   history and blame for free, and `/cleanup-todos` Step 7's existing "if this project tracks
   `.claude/todos/` in git, run `/commit` at the end" branch starts firing. Cost: backlog churn
   lands in the same history as skill changes, and `done/` is ~104 files and growing.
2. **Track only the active backlog**, not `done/` - same as above plus an ignore for
   `.claude/todos/done/`. Keeps history readable; loses the archive.
3. **Leave untracked, mandate a snapshot** - require any bulk rewrite of the folder to zip it first,
   written into `ai-todos-format.md` rather than left to whoever remembers.

Check whether other project backlogs are tracked before choosing, so the answer is consistent with
what `ai-todos-format.md`'s git-policy section already says rather than a one-off for this repo.

## Acceptance

- `.gitignore`'s treatment of `.claude/todos/` is deliberate and matches `ai-todos-format.md`'s
  stated git policy.
- If tracked: `git ls-files .claude/todos/` is non-empty and `/cleanup-todos`'s commit branch fires.
- If left untracked: the snapshot requirement is written into `ai-todos-format.md`, not folklore.

## Notes

- Filed by `/close` on 2026-08-12. Surfaced twice during that session and deferred both times.
