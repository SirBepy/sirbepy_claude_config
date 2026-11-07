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
  - From the Bash tool on Windows, a `--hunk path:substring` whose substring begins with a slash is rewritten by MSYS path conversion (the colon becomes `;` and the slashes become backslashes, so the script rejects it as `--hunk expects path:substring`). Use the PowerShell tool, or set `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*` and pass the script path in `C:/` form (`C:/Users/tecno/.claude/skills/commit/split-hunks.py`), because those variables also stop a `~/.claude/...` script path from converting.
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

`release.py bump` (used by `/commit v` and `/release`) widens to Rust crates
when `src-tauri/Cargo.toml` exists:

1. It rewrites the `version = "..."` line under `[package]` to the new version.
2. It edits only that package's own `Cargo.lock` entry, line-targeted, with no
   `cargo` regeneration.
3. Both files appear in the printed `files`, which is step 8's pathspec.
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

## Branch protection (step 1a)

Verbatim step 1a from the pre-split `SKILL.md`; the bookkeeping lists it initialises (EXPECTED branch and sha, OWN-COMMIT list, overlap queue, session-scoped lists) stay in `SKILL.md` step 1a.

1a. **Branch-protection check** - convention-driven, not branch-name-driven, so it only fires where a repo has actually opted in. Run `git rev-parse --abbrev-ref HEAD` and record the result as this run's EXPECTED branch, and `git rev-parse HEAD` as this run's EXPECTED sha (step 8 re-checks both against it before every commit - the sha catches a peer commit that landed on the SAME branch, which a branch-name-only check would miss). Also start this run's OWN-COMMIT list empty and its overlap queue empty (step 8 appends to both - todo 860). These two are per-run; two more are session-scoped and survive across separate `/commit` invocations in the same session, so only initialize them if this is the session's first invocation: this session's cumulative own-commit list (every sha this session has committed, appended alongside the per-run list at step 8's post-commit line), and this session's fold-policy, unset until step 8's end-of-queue question is first answered (todo 862). If ALL three hold - the branch matches a protected-trunk name (`main`, `master`, `develop`, or a project override), the repo has a remote (`git remote` is non-empty), and a `GIT_FLOW.md` (or an equivalent documented trunk-protection rule in root `CLAUDE.md`) exists at the repo root - stop and ask via `AskUserQuestion`: branch first, commit anyway (explicit override), or abort. Repos with no such documented convention are unaffected, protected-sounding branch name or not - this explicitly does NOT fire on `~/.claude` itself, which commits to `master` by design and has no `GIT_FLOW.md`.

## Submodule check (step 7)

7. **Submodule check:** run `git submodule status` (no flags). For each submodule whose sha is prefixed with `+` (modified) or `-` (uninitialized/not checked out), handle it before committing the parent:
   - If prefixed with `-`: warn the user, do not auto-commit an uninitialized submodule.
   - If prefixed with `+` (dirty pointer: submodule has new commits not yet staged in parent): this is fine, include `<submodule-path>` in step 8's commit pathspec and the pointer bump lands with the parent commit.
   - If the submodule itself has **uncommitted working-tree changes** (detected via `git -C <submodule-path> status --porcelain`): run the 4-step submodule commit flow first:
     1. `git -C <submodule-path> add <changed files by name>` - stage changed files inside the submodule.
     2. `git -C <submodule-path> commit -m "<message>"` - commit inside the submodule using the same prefix/style rules as the parent commit.
     3. Include `<submodule-path>` in step 8's commit pathspec - a gitlink path commits the submodule's current HEAD, so no `git add` is needed in the parent.
     4. Then continue to step 8 as normal; the parent commit will include the pointer bump.
   - If no submodules or all are clean: skip this step silently.
