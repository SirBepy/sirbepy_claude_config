# Commit edge cases

Read on demand from `/commit` - merges, partial staging, and backdating are
rare paths, not part of the normal flow.

## Merge commits

Merges go through this skill's flow too - never a raw `git merge` + push that lands an unreviewed merge commit, never `git commit` directly, and never a raw `git cherry-pick` either: it creates a commit the same way `git commit` does, bypassing the marker gate just as easily. Make sure this session's commit-marker exists before it runs (see the commit-guard section above). Unlike a merge, a cherry-pick's message usually keeps the original commit's message as-is - it's carrying forward an already-reviewed commit, so there's no `MERGE:`-style rewrite; the marker is the only thing it's missing.

- **When a merge is needed:** a non-fast-forward push (remote has commits local never pulled) or deliberately absorbing superseded remote history into a new line of work.
- **Prefer the least-surprising resolution.** If a plain `git pull --no-rebase` merges cleanly and the result is what you want, take it. Only reach for `git merge -s ours <remote-ref>` when you intentionally want to KEEP local content and record the remote history as absorbed-but-superseded (e.g. an old framework version preserved on a legacy branch).
- **Message:** use a `MERGE:` prefix and state plainly what was absorbed and where the superseded content still lives, e.g. `MERGE: absorb remote React v2.7 into history (content preserved on legacy/react-v2; Flutter tree unchanged)`.
- **Hard stops still apply.** `git rebase` (rewrites shared history) and force-push are NOT merge resolutions - do not reach for them to avoid a merge commit. In an autopilot/unattended run, force-push is a hard stop; park it rather than guessing.

## Splitting one file across commits (partial staging)

When a single file holds changes belonging to different commits, stage the specific hunks - do NOT commit the whole file, and do NOT mutate the working tree (delete progress → commit → undo) to fake it.

- `git add -p` is the usual way, but it's INTERACTIVE and hangs in this non-interactive shell. Do not use it.
- The hand-rolled non-interactive route (`git diff <file> > <tmp>.patch`, trim hunks by hand, `apply --cached --recount <tmp>.patch`) has two traps hit in practice (todos 1046, 1068):
  - The `>` redirect is a shell content-write hooks/shell-content-write-guard.py denies outright, so the documented command is uncallable as written.
  - Piping the patch through a text-mode subprocess turns `\n` into `\r\n` on Windows, which breaks `git apply`'s context match ("patch does not apply") even though the patch text looked right.
  - Committing straight from the real index risks sweeping in a concurrent session's staged files, and racing a peer's commit between staging and committing can silently revert their work entirely (a stale tree landing on their new HEAD looks like a normal commit, but `git show --stat` lists THEIR files as deleted).
- Use `skills/commit/split-hunks.py` instead - it does the same diff/trim/apply mechanically, in bytes mode (no CRLF trap) with no shell redirect (nothing for the write guard to catch):
  - **Solo case, nothing else of interest staged:**
    `python skills/commit/split-hunks.py --repo <path> stage <file> --match <substring>`
    Filters `<file>`'s unstaged hunks (vs HEAD) to the ones whose added/removed lines contain `<substring>`, applies just those into the real index with `git apply --cached`. Verify with `git diff --cached -- <file>`, same as before.
  - **Shared-index case, a concurrent session has staged work or could commit while you're mid-split:**
    `python skills/commit/split-hunks.py --repo <path> commit -m "<message>" --whole <file> [--whole <file> ...] --hunk <file>:<substring> [--hunk <file>:<substring> ...]`
    Records `base=$(git rev-parse HEAD)` first, builds a private `GIT_INDEX_FILE` seeded from `base` (never the shared one), stages declared whole files and filtered hunks into it, refuses before creating any commit object if the resulting tree touches a path outside what was declared, then commits and lands it with `git update-ref HEAD <new> <base>` - a compare-and-swap that refuses outright (leaving HEAD exactly where the peer left it) if HEAD moved since `base` was read. On success it resyncs the real index's entries for the committed paths only (`git reset -q -- <paths>`), never touching anything else a concurrent session staged. On a lost race, rerun with `--base <the new HEAD>` to retry.
  - `commit-tree`/`update-ref` are a different subcommand token than `git commit`, so hooks/commit-guard.py's marker gate and prefilter re-check never see this path; `commit` mode runs `prefilter-gate.sh` itself over the declared pathspec before building the commit, so that protection isn't silently skipped.
  - Self-test: `bash skills/commit/test_split_hunks.sh` (covers the no-match case, the shared-index survival case, and the CAS race).
- Verify the partially-staged/committed result compiles/lints on its own (the committed state must build without the unstaged remainder).
- This is surgical and leaves the working tree untouched - prefer it over restore-edit-amend whenever you need exact lines.
- **Exception to step 8's pathspec rule:** a hunk-level split genuinely needs the index (that's what `apply --cached` stages into), so `stage` mode's result is the one case committed FROM the index instead of by pathspec - re-run `git diff --cached --stat` immediately before that commit to confirm the index holds ONLY the hunks just staged. `commit` mode above never has this exposure: it builds and verifies the tree in a private index before HEAD ever moves, so there is nothing left to "stop and re-isolate" from.

## Foreign hunk inside your own hunk

When `foreign-hunk-check.sh` (step 8's working-tree diff check) reports `foreign-hunks-inside-your-hunk`, a peer's uncommitted lines and yours share one `@@` block - `git apply --cached` cannot split a hunk, so a pathspec commit of that file takes both. Two safe orders, no third:

- **Peer commits first.** Once their commit lands, `git diff HEAD` for that file now shows only your remaining delta (their part already matches the new HEAD) - rerun the check to confirm clean, then commit normally.
- **Reconstruct the blob yourself**, same patch-trim technique as "Splitting one file across commits" above: dump the diff, delete the peer's hunk lines by hand, `apply --cached --recount`, verify, commit from the index.

## Shared-checkout hook hazard

A pathspec commit (step 8) protects the INDEX from a concurrent session's
staged files. It protects nothing in the WORKING TREE, and a pre-commit hook
that stages, stashes, or hides files (e.g. husky + lint-staged's "Backing up
original state" / "Hiding unstaged changes") operates on the working tree
directly. If that hook fails mid-run - most commonly a `.git/index.lock`
collision with another session sharing this `.git` - its restore step can be
skipped, deleting another session's unstaged edits from disk.

**Preflight:** before a hook-bearing commit, check `git rev-parse
--git-common-dir` against `--git-dir` (differ = worktree) and whether
`.git/index.lock` exists. Either true = prefer `--no-verify`, and run the
project's formatter and linter by hand first so the hook's checks still
happen, just not inside the hook.

**Recovery**, if a hook already ate someone's unstaged changes: lint-staged
leaves them at `.git/lint-staged_unstaged.patch` - apply with `git apply`
(`--recount` if hand-trimmed first).

## Cargo.toml version bump (Tauri apps)

`/commit v`'s step 2 widens to Rust crates when `src-tauri/Cargo.toml` (or any
`Cargo.toml` whose `[package]` name matches the app) exists:

1. Rewrite its `version = "..."` line under `[package]` to the new version.
2. Regenerate `Cargo.lock` via cargo, never hand-edit: `cargo check` from the
   crate dir (or `cargo update -p <crate> --precise <new-version>` if a full
   check is too slow).
3. Include both `Cargo.toml` and `Cargo.lock` in step 8's pathspec.
4. Scope to the app crate only - never bump a workspace member or a
   vendored/submodule crate (e.g. `vendor/tauri_kit`) alongside the app.

## Backdating commits

- When the user asks for a specific commit time, jitter it to look organic:
  - Always randomize the seconds (00-59).
  - Shift the minutes by a few (typically +/- 1-4) from whatever was requested.
  - Example: user says "27 minutes after the previous commit" → don't use exactly :45:00; use :43:17, :46:52, etc.
- Apply the same timestamp to both author and committer dates: `GIT_COMMITTER_DATE="..." git ... commit --date="..." ...`.
- Confirm the resulting timestamp back to the user after committing.
- **Client repos** (`refs/client-repos.txt`): backdating is only for a time Joe explicitly names, and never into 23:00-10:59 or as a way to move a night commit out of that window. `hooks/commit-window-guard.py` refuses `--date`/`GIT_*_DATE` there whenever the value lands in the window, has no readable HH:MM, or the commit runs inside the window. A `/commit fold` replaying a commit that really was made at night needs Joe's approval and the hook's `allow` first.
