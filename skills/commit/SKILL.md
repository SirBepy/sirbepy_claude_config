---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, pushbump, pushnbump) to commit changes.
argument-hint: "[v|bump|push|pushbump|pushnbump|onlyv|onlybump]"
---

# /commit

> Commit changes into clean, well-organized commits.

## `/commit`

**Commit-guard marker:** a global PreToolUse hook blocks raw `git commit`. Before the FIRST `git commit` call of a session, write a session marker, in its OWN tool call, never chained with the commit (`;`/`&&`) - the hook inspects the whole command string BEFORE any of it runs, so a chained marker does not exist yet at hook time and the call is always rejected whole, nothing in it executes:

```powershell
Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-session-$env:CLAUDE_CODE_SESSION_ID" -Value "x"
```

The marker is keyed to this session and is never consumed, so every later commit in the same session needs no marker write at all - just call `git commit` directly. A raw `git commit` from a session that never wrote this marker is still blocked, and two concurrent sessions can never share or steal each other's marker since each is keyed to its own session id.

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.), including a documented "pre-commit hook reformats beyond the staged diff" note - if present, follow its stated `--no-verify` authorization and size threshold exactly. Absent such a note, never bypass a hook on your own judgment - except the shared-checkout hazard in step 8, which applies regardless of commit-style.md. Only read it once per session.
1a. **Branch-protection check** - convention-driven, not branch-name-driven, so it only fires where a repo has actually opted in. Run `git rev-parse --abbrev-ref HEAD` and record the result as this run's EXPECTED branch (step 8 re-checks against it before every commit). If ALL three hold - the branch matches a protected-trunk name (`main`, `master`, `develop`, or a project override), the repo has a remote (`git remote` is non-empty), and a `GIT_FLOW.md` (or an equivalent documented trunk-protection rule in root `CLAUDE.md`) exists at the repo root - stop and ask via `AskUserQuestion`: branch first, commit anyway (explicit override), or abort. Repos with no such documented convention are unaffected, protected-sounding branch name or not - this explicitly does NOT fire on `~/.claude` itself, which commits to `master` by design and has no `GIT_FLOW.md`.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Comment-noise and em-dash check** (always runs, no size/skip-review gate - unlike `/close`'s conditional `/code-check` pass, this fires on every commit, no exception for a small diff). Run both via Bash, replacing `<files>` with the paths this commit will touch, including not-yet-`git add`ed new files - each script's untracked-file pass is what makes those visible, since a bare `git diff HEAD` cannot see them:

    ```
    bash skills/commit/comment-noise.sh <files>
    bash skills/commit/em-dash.sh <files>
    ```

    No output from either = clean, continue. Comment-noise flagged = trim the offending blocks now - per the cap in `skills/commit/comment-noise.md` (2 lines typical, 4 hard per block, 25% ratio once a file adds 20+ lines) - before committing, don't ask, matching `/create-pr` step 2b's auto-trim. **Exception:** a block flagged only because it moved verbatim from elsewhere in this same commit is not new noise - confirm via `git show HEAD:<old-file>` before trimming it, see comment-noise.md's judge step. Em-dash flagged = fix that added line now, same don't-ask treatment; the script only looks at added lines, so a pre-existing em dash on an unchanged line never gets reported and needs no exception. `comment-noise.md`/`comment-noise.sh`/`em-dash.sh` stay the one place the cap number and the prefilter commands are defined; this step just invokes them.
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
7a. **Peer check:** call `list_peers`. If it shows another active session in this repo, call `post_message` naming the pathspec about to be committed, then proceed - this applies even inside a dedicated worktree, since collisions happen at merge time, not on disk. Both are MCP tools that may not exist in a plain terminal session; if either tool is unavailable, skip this step silently.
8. **Commit by pathspec, never stage-then-commit.** Four preconditions, checked right here, not skimmed past earlier - all required, every single commit, not once per run:
   - Have step 5a's prefilters actually been run against this exact pathspec, this turn, and come back clean or already-trimmed? If not, stop and run them now - do not call `git commit` first and rationalize the check afterward.
   - **Step 1 re-check:** if `.claude/commit-style.md` exists in this repo and hasn't actually been read this session (not "probably was"), read it now before continuing.
   - **Branch guard:** run `git rev-parse --abbrev-ref HEAD` again, right now - not the value step 1a recorded minutes ago. If it differs from step 1a's EXPECTED branch, or prints `HEAD` (detached), STOP: do not commit, and surface both branch names to the dev. A pathspec commit protects the INDEX from a concurrent session's staged files; it says nothing about which BRANCH receives the commit, and a multi-commit sweep leaves plenty of time for another session sharing this checkout to move HEAD underneath it.
   - **Unpushed-overlap check:** `git log @{u}..HEAD --format='%h'` (skip silently, no upstream). For each sha, `git show --name-only --format= <sha>` and intersect with this commit's pathspec. Any overlap: STOP, name the overlapping commit, ask whether this is follow-up on the same unit of work (-> `git reset --soft HEAD~1`, restage everything together, one fresh commit) or genuinely separate (-> proceed).

   **Shared-checkout hook hazard:** if this repo has a pre-commit hook configured (`git config core.hooksPath`) and is a shared `.git` checkout (`git rev-parse --git-common-dir` differs from `--git-dir`, or `.git/index.lock` exists) - add `--no-verify` below and run the project's formatter/linter by hand first. A hook that stages, stashes, or hides files is a WORKING-TREE risk that pathspec commits do not cover. Full reasoning and recovery: `skills/commit/edge-cases.md`.

   Then run `git commit -m "<message>" -- <file> <file> ...`, naming every path this commit should contain. This commits exactly those paths' current working-tree state and never reads the index, so it is correct whether or not a concurrent session sharing this repo's `.git/index` has its own work staged there. No shared-index check is needed and none should be run - the form is unconditional.
   - **Untracked files are the one exception:** a pathspec cannot name a file git doesn't know yet, so `git add <new-file> <new-file>` them first, then include them in the same pathspec commit. That add only ever touches your own paths.
   - Never `git reset` or unstage entries you didn't stage - that disrupts another session's commit prep. **Exception:** the unpushed-overlap check above, which is a deliberate, surfaced `reset --soft` on your own prior commit, never someone else's.
   - Accepted trade-off: there is no `git diff --staged` review before the commit, so check the file list against the `git status` / `git diff` output from steps 2-3 before running it.
   - After a multi-commit sweep, sanity-check with `git merge-base --is-ancestor <last-sha> <expected-branch>` to confirm nothing landed off-branch.
8b. **Post-commit index refresh, only if the repo runs `lint-staged` on pre-commit** (check `git config core.hooksPath` and read the resulting `pre-commit` file for a `lint-staged` call). That hook rewrites the just-committed files in place and applies the result into the commit, which leaves their index entries stat-dirty against the rewritten working tree even though `git diff HEAD` is empty. Fix: `git add` the exact paths just committed, and print which ones. Do NOT use `git reset` here - a shared checkout may have another session's work staged, and reset would disrupt it. Do NOT use `git update-index --refresh` either - it only reports "needs update" per file and stops, it doesn't fix anything.

If nothing to commit, say so and stop.

## `/commit v` / `/commit bump`

Same as `/commit` but also bumps the patch version before committing (e.g. 1.0.0 -> 1.0.1).

Version bump procedure:
1. Find `package.json` in the repo root. If it exists, it is the **source of truth** - read the version from it, increment the patch number, and write it back.
2. Find any other `.json` files in the repo root that contain a top-level `"version"` field (e.g. `tauri.conf.json`, `manifest.json`). Update each one to match the new version. If a Rust crate manifest exists for the app (`src-tauri/Cargo.toml`), it needs the same bump too - see `skills/commit/edge-cases.md` for the lockfile-regen and scope rules.
3. Include all modified version files in step 8's commit pathspec, alongside the other changed files.

Commit message follows the normal style - no need to mention the version bump.

If no `package.json` exists, skip the version step and commit normally.

## `/commit push`

Same as `/commit` but also runs `git push` after committing.

**Push rule:** if the commit step failed, do not push. If there was nothing to commit, don't stop there either - check `git rev-list --count @{u}..HEAD` (if `@{u}` doesn't resolve, say so and offer `git push -u origin <branch>` instead of silently doing nothing). Zero ahead: say "nothing to commit, nothing to push" and stop. One or more ahead: push those existing commits and report how many.

After a successful push, run the **Build watch** (see `skills/commit/build-watch.md`).

## `/commit pushbump`

Same as `/commit v` but also runs `git push` after committing.

Same push rule as `/commit push` above.

After a successful push, run the **Build watch** (see `skills/commit/build-watch.md`).

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

Do not push if either commit step failed. Otherwise same push rule as `/commit push` above - a clean-tree branch that's still ahead of its upstream still gets pushed, it just won't happen here since the version commit always produces new changes.

After a successful push, run the **Build watch** - see `skills/commit/build-watch.md` for the full detect/launch/gated-auto-fix procedure (not needed for a plain `/commit`).

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
- Never use `cd` before git commands. Use `git -C /absolute/path <command>`.
- **Target repo other than cwd:** if the dev or a prior instruction names a repo path other than the current project, use `git -C <path>` for every git command this run issues, not just some of them, and state that repo path back in the first line of output so it's unambiguous which repo is being committed to.
- Name every path in the commit pathspec (step 8). Never `git add -A`, never `git commit -a`. **Exception - mass deletion/move of tracked files:** when a commit's whole purpose is deleting or moving many tracked files (e.g. a framework rewrite wiping an old tree), naming each path is impractical; pass the containing tree instead - `git commit -m "<message>" -- <tree-path>` - never a bare repo-wide pathspec (which would also sweep in any unrelated uncommitted edits sitting elsewhere in the repo). A pathspec only picks up already-tracked files, never untracked ones, so it stays within the "know what you're committing" intent while `-A` does not. Sanity-check `git status` after, and if the deletion set is mixed with unrelated edits, split them.

## Edge cases: merges, partial staging, backdating

Rare paths, read on demand: `skills/commit/edge-cases.md` covers merge-commit resolution, splitting one file's changes across separate commits (partial staging), and backdating commit timestamps.

## Grouping: shared-component swaps

When a file's only change is swapping a local implementation for a shared / design-system component, it belongs with the commit that adds or changes that shared component - not the feature commit that happened to trigger the swap. If that file also carries feature-specific edits, split it via partial staging (`skills/commit/edge-cases.md`): swap hunks go with the component commit, the rest with the feature.
