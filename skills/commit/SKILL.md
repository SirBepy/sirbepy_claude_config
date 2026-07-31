---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, pushbump, pushnbump) to commit changes.
argument-hint: "[v|bump|push|pushbump|pushnbump|onlyv|onlybump]"
---

# /commit

> Commit changes into clean, well-organized commits.

## `/commit`

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.). Only read it once per session.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Comment-noise check** (always runs, no size/skip-review gate - unlike `/close`'s conditional `/code-check` pass, this fires on every commit). Run the same mechanical prefilter as `/create-pr`'s Comment-noise check (see `create-pr/SKILL.md` for the cap definition and exact command), scoped to the diff about to be committed (`git diff HEAD -- <files>` in place of `<base>..HEAD`). No output = clean, continue. Flagged = trim the offending blocks now, per that same rule, before committing - don't ask, matching `/create-pr` step 2b's auto-trim.
6. Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait for the result. If it fails, **abort the commit**, print the failing output, and explain to the user exactly why the commit was aborted (which command failed, what it printed, and that they need to fix it or tell you to skip). Do not stage or commit anything until the user either fixes it or explicitly says to skip.
7. **Submodule check:** run `git submodule status` (no flags). For each submodule whose sha is prefixed with `+` (modified) or `-` (uninitialized/not checked out), handle it before committing the parent:
   - If prefixed with `-`: warn the user, do not auto-commit an uninitialized submodule.
   - If prefixed with `+` (dirty pointer — submodule has new commits not yet staged in parent): this is fine, include `<submodule-path>` in step 8's commit pathspec and the pointer bump lands with the parent commit.
   - If the submodule itself has **uncommitted working-tree changes** (detected via `git -C <submodule-path> status --porcelain`): run the 4-step submodule commit flow first:
     1. `git -C <submodule-path> add <changed files by name>` — stage changed files inside the submodule.
     2. `git -C <submodule-path> commit -m "<message>"` — commit inside the submodule using the same prefix/style rules as the parent commit.
     3. Include `<submodule-path>` in step 8's commit pathspec — a gitlink path commits the submodule's current HEAD, so no `git add` is needed in the parent.
     4. Then continue to step 8 as normal; the parent commit will include the pointer bump.
   - If no submodules or all are clean: skip this step silently.
8. **Commit by pathspec, never stage-then-commit.** Run `git commit -m "<message>" -- <file> <file> ...`, naming every path this commit should contain. This commits exactly those paths' current working-tree state and never reads the index, so it is correct whether or not a concurrent session sharing this repo's `.git/index` has its own work staged there. No shared-index check is needed and none should be run - the form is unconditional.
   - **Untracked files are the one exception:** a pathspec cannot name a file git doesn't know yet, so `git add <new-file> <new-file>` them first, then include them in the same pathspec commit. That add only ever touches your own paths.
   - Never `git reset` or unstage entries you didn't stage - that disrupts another session's commit prep.
   - Accepted trade-off: there is no `git diff --staged` review before the commit, so check the file list against the `git status` / `git diff` output from steps 2-3 before running it.

If nothing to commit, say so and stop.

## `/commit v` / `/commit bump`

Same as `/commit` but also bumps the patch version before committing (e.g. 1.0.0 -> 1.0.1).

Version bump procedure:
1. Find `package.json` in the repo root. If it exists, it is the **source of truth** - read the version from it, increment the patch number, and write it back.
2. Find any other `.json` files in the repo root that contain a top-level `"version"` field (e.g. `tauri.conf.json`, `manifest.json`). Update each one to match the new version.
3. Include all modified version files in step 8's commit pathspec, alongside the other changed files.

Commit message follows the normal style - no need to mention the version bump.

If no `package.json` exists, skip the version step and commit normally.

## `/commit push`

Same as `/commit` but also runs `git push` after committing.

Do not push if the commit failed or there was nothing to commit.

After a successful push, run the **Build watch** (see below).

## `/commit pushbump`

Same as `/commit v` but also runs `git push` after committing.

Do not push if the commit failed or there was nothing to commit.

After a successful push, run the **Build watch** (see below).

## `/commit pushnbump`

Commits changes and version as **two separate commits**, then pushes.

Order:
0. **Kit sync (before anything else):** if `vendor/tauri_kit` exists as a submodule, pull its latest remote commits:
   - Record the current SHA: `git submodule status vendor/tauri_kit` (note the sha before the space).
   - Run `git submodule update --remote vendor/tauri_kit`.
   - Check if the SHA changed by running `git submodule status vendor/tauri_kit` again.
   - If it changed: commit it as a standalone commit by pathspec, `git commit -m "CHORE: bump tauri_kit <old-short-sha> → <new-short-sha>" -- vendor/tauri_kit` (7-char shas). This commit lands before the main changes commit so the two concerns stay separate in git blame.
   - If unchanged or the submodule doesn't exist: skip silently.
1. Do the normal commit for changed files (same as `/commit`).
2. Bump the patch version (same procedure as `/commit v`).
3. Commit ONLY the version files, by pathspec: `git commit -m "<message>" -- <version-file> ...`.
4. Message: `VERSION: <new-version>` — where `<new-version>` is the full version string after bumping. If a build number field (e.g. `"build"` in `package.json` or `tauri.conf.json`) exists alongside the version, append it: `VERSION: 1.0.1+21`.
5. Run `git push`.

Do not push if either commit failed or there was nothing to commit.

After a successful push, run the **Build watch** (see below).

## Build watch (after any push variant)

After a successful `git push` in `push`, `pushbump`, or `pushnbump`, watch the GitHub Actions run(s) that push triggered. A single push can kick off several workflows (test + lint + build); the watcher tracks **all** runs for the pushed sha and reports failure if any of them fails. **Non-blocking**: launch the watcher in the background, tell the user it's watching, and yield control immediately. The user can ignore it or say "drop it" to stop caring.

Steps:

1. **Clear the loop-breaker marker for a fresh manual push.** If this push was initiated directly by the user (not a re-push from a prior auto-fix), delete `<git-dir>/commit-buildwatch-autofixed` if it exists. (`<git-dir>` = `git -C <path> rev-parse --git-dir`.) This gives each manual push its own one-shot auto-fix budget.
2. **Detect CI.** Only watch if ALL hold: `gh` is installed (`gh --version` succeeds), the repo has a GitHub remote (`gh repo view` succeeds), and `.github/workflows/` exists with at least one workflow file. If any fail, skip the watch silently - no message, no script launch.
3. **Launch the watcher in the background.** Get the branch (`git -C <path> rev-parse --abbrev-ref HEAD`), then run, in the background, WITHOUT a `-Sha` argument - the script resolves HEAD itself via `-RepoPath`, so there's no hand-typed sha to get wrong:

   `& "C:\Users\tecno\.claude\skills\commit\watch-build.ps1" -Branch <branch> -RepoPath <path>`

   Use a literal path (never `$env:`-built) so it doesn't trigger a permission prompt.
4. **Announce and move on.** Tell the user: "Pushed. Watching the CI build in the background - I'll ping you when it lands. Say 'drop it' to ignore." Do NOT block or poll; you'll be re-invoked when the watcher exits.

When the watcher finishes you are re-invoked with its stdout. Parse the `BUILD_RESULT` marker:

- `BUILD_RESULT=success` -> all runs passed (the marker lists how many + their workflow names). Tell the user the build passed. Delete the `commit-buildwatch-autofixed` marker if present. Done.
- `BUILD_RESULT=no_run` -> no run registered for the pushed sha within ~3 min. Tell the user you couldn't find a CI run (it may not have triggered) and stop. Do not relaunch the watcher.
- `BUILD_RESULT=failure` -> the build is red. Run the **gated auto-fix** below.
- `BUILD_RESULT=watch_error` -> `gh` hit a persistent transient error (auth flip, network blip, rate limit) while polling and could not confirm a completed status for one or more runs after retrying with backoff. This is NOT a build verdict - the run(s) may still be green, red, or in progress. Tell the user the watcher couldn't confirm the result and relaunch it (same command as before) rather than diagnosing a "failure" that might not exist.

### Gated auto-fix

The watcher prints the failed-step logs after a `failure` marker. Diagnose from them, then branch:

- **First, check the loop-breaker.** If `<git-dir>/commit-buildwatch-autofixed` already exists, the one-shot budget is spent: go straight to **STOP and ask** with the new logs. Do not auto-fix.
- **Auto-fix, then re-commit and push without asking** ONLY when ALL hold:
  1. It's a real code failure (test, typecheck, lint, build/compile error) - NOT infra (runner timeout, network, expired secret, rate limit, obvious flake).
  2. The failure traces to files in the diff you just pushed.
  3. The fix is mechanical / unambiguous.

  When all three hold: write the marker file `<git-dir>/commit-buildwatch-autofixed` (records the one-shot is now used), apply the fix, run the project's fast checks locally to confirm green, then re-commit and push via `/commit push` (per the global rule, never commit directly). That re-push starts a fresh build watch automatically - the marker ensures a second failure can't trigger another auto-fix.
- **Otherwise: STOP and ask.** Show the diagnosis and the proposed fix, then ask the user (AskUserQuestion) to approve before changing anything. This covers infra/flake failures, failures in files you didn't touch, and any judgment-call fix.

## `/commit onlyv` / `/commit onlybump`

Only bumps the patch version. No other changes staged.
Commit message is always: `CHORE: bump to v1.0.1` (with the actual new version).

Version bump procedure: same as `/commit v` above.

If no `package.json` exists, say so and stop.

## Prefixes

- `FEAT:` - new feature
- `FIX:` - bug fix
- `REFACTOR:` - code restructure, no behavior change
- `CHORE:` - maintenance, config, tooling
- `DOCS:` - readme, comments, documentation
- `TEST:` - adding or updating tests
- `STYLE:` - formatting only, no logic change
- `DATA:` - hardcoded data, content, or copy changes

## Rules

- Project `.claude/commit-style.md` overrides these rules when present.
- One purpose per commit. Many files is fine if it's one logical change.
- Prefer more commits over fewer big ones. Split unrelated changes.
- Message title alone should make clear what was done.
- No body unless something genuinely needs explanation.
- Never add `Co-authored-by: Claude` or any AI attribution.
- Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
- Never use `cd` before git commands. Use `git -C /absolute/path <command>`.
- Name every path in the commit pathspec (step 8). Never `git add -A`, never `git commit -a`. **Exception - mass deletion/move of tracked files:** when a commit's whole purpose is deleting or moving many tracked files (e.g. a framework rewrite wiping an old tree), naming each path is impractical; pass the containing tree instead - `git commit -m "<message>" -- <tree-path>` - never a bare repo-wide pathspec (which would also sweep in any unrelated uncommitted edits sitting elsewhere in the repo). A pathspec only picks up already-tracked files, never untracked ones, so it stays within the "know what you're committing" intent while `-A` does not. Sanity-check `git status` after, and if the deletion set is mixed with unrelated edits, split them.

## Merge commits

Merges go through this skill's flow too - never a raw `git merge` + push that lands an unreviewed merge commit, and never `git commit` directly.

- **When a merge is needed:** a non-fast-forward push (remote has commits local never pulled) or deliberately absorbing superseded remote history into a new line of work.
- **Prefer the least-surprising resolution.** If a plain `git pull --no-rebase` merges cleanly and the result is what you want, take it. Only reach for `git merge -s ours <remote-ref>` when you intentionally want to KEEP local content and record the remote history as absorbed-but-superseded (e.g. an old framework version preserved on a legacy branch).
- **Message:** use a `MERGE:` prefix and state plainly what was absorbed and where the superseded content still lives, e.g. `MERGE: absorb remote React v2.7 into history (content preserved on legacy/react-v2; Flutter tree unchanged)`.
- **Hard stops still apply.** `git rebase` (rewrites shared history) and force-push are NOT merge resolutions - do not reach for them to avoid a merge commit. In an autopilot/unattended run, force-push is a hard stop; park it rather than guessing.

## Splitting one file across commits (partial staging)

When a single file holds changes belonging to different commits, stage the specific hunks - do NOT commit the whole file, and do NOT mutate the working tree (delete progress → commit → undo) to fake it.

- `git add -p` is the usual way, but it's INTERACTIVE and hangs in this non-interactive shell. Do not use it.
- Non-interactive route instead:
  1. `git -C <path> diff <file> > <tmp>.patch` (or `diff HEAD <file>`).
  2. Edit the patch: delete the hunks you don't want. Keep the `diff --git`/`index`/`---`/`+++` header lines and the `@@` line of each hunk you keep. Don't bother renumbering `@@` counts.
  3. `git -C <path> apply --cached --recount <tmp>.patch` (`--recount` tolerates off `@@` counts from hand-trimming). If it still rejects on context mismatch, re-dump and re-trim rather than forcing.
  4. Verify the partially-staged result compiles/lints on its own (the committed state must build without the unstaged remainder), then commit.
- This is surgical and leaves the working tree untouched - prefer it over restore-edit-amend whenever you need exact lines.
- **Exception to step 8's pathspec rule:** a hunk-level split genuinely needs the index (that's what `apply --cached` stages into), so it is the one case that commits FROM the index instead of by pathspec. Re-run `git diff --cached --stat` immediately before committing to confirm the index holds ONLY the hunks you just staged - if a concurrent session added anything else in between, stop and re-isolate rather than committing whatever the index now contains.

## Grouping: shared-component swaps

When a file's only change is swapping a local implementation for a shared / design-system component, it belongs with the commit that adds or changes that shared component - not the feature commit that happened to trigger the swap. If that file also carries feature-specific edits, split it via partial staging above: swap hunks go with the component commit, the rest with the feature.

## Backdating commits

- When the user asks for a specific commit time, jitter it to look organic:
  - Always randomize the seconds (00-59).
  - Shift the minutes by a few (typically +/- 1-4) from whatever was requested.
  - Example: user says "27 minutes after the previous commit" → don't use exactly :45:00; use :43:17, :46:52, etc.
- Apply the same timestamp to both author and committer dates: `GIT_COMMITTER_DATE="..." git ... commit --date="..." ...`.
- Confirm the resulting timestamp back to the user after committing.
