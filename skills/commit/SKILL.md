---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, pushbump, pushnbump) to commit changes.
argument-hint: "[v|bump|push|pushbump|pushnbump|onlyv|onlybump]"
---

# /commit

> Commit changes into clean, well-organized commits.

## `/commit`

**Commit-guard marker:** a global PreToolUse hook blocks raw `git commit`. Before EVERY `git commit` call this skill issues, without exception, write a uniquely-suffixed marker:

```powershell
Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"
```

Each commit writes its own fresh marker; the hook consumes the oldest fresh one and leaves the rest, so two concurrent sessions can no longer consume each other's marker. The hook needs a marker written within the last 2 minutes, so redo this before each individual commit, not once for the whole flow.

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.). Only read it once per session.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Comment-noise check** (always runs, no size/skip-review gate - unlike `/close`'s conditional `/code-check` pass, this fires on every commit, no exception for a small diff). Run this exact command, replacing `<files>` with the paths this commit will touch, including not-yet-`git add`ed new files - the untracked-file pass below is what makes those visible, since a bare `git diff HEAD` cannot see them:

    ```
    { git diff HEAD -- <files>; git status --porcelain -- <files> | awk '$1=="??"{print substr($0,4)}' | while IFS= read -r f; do git diff --no-index -- /dev/null "$f"; done; } | awk '
    /^\+\+\+ b\// { f=substr($0,7); run=0; next }
    /^\+/ && !/^\+\+\+/ {
      l=substr($0,2); add[f]++
      if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
      next
    }
    { run=0 }
    END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }' | sort
    ```

    No output = clean, continue. Flagged = trim the offending blocks now - per the cap in `skills/commit/comment-noise.md` (2 lines typical, 4 hard per block, 25% ratio once a file adds 20+ lines) - before committing, don't ask, matching `/create-pr` step 2b's auto-trim. `comment-noise.md` stays the one place the cap number and `/create-pr`'s range-mode variant of this command are defined; this copy is kept in sync with it, not a separate rule.
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
8. **Commit by pathspec, never stage-then-commit.** Precondition, checked right here, not skimmed past earlier: has step 5a's prefilter actually been run against this exact pathspec, this turn, and come back clean or already-trimmed? If not, stop and run it now - do not call `git commit` first and rationalize the check afterward. Then run `git commit -m "<message>" -- <file> <file> ...`, naming every path this commit should contain. This commits exactly those paths' current working-tree state and never reads the index, so it is correct whether or not a concurrent session sharing this repo's `.git/index` has its own work staged there. No shared-index check is needed and none should be run - the form is unconditional.
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

After a successful push, run the **Build watch** (see `skills/commit/build-watch.md`).

## `/commit pushbump`

Same as `/commit v` but also runs `git push` after committing.

Do not push if the commit failed or there was nothing to commit.

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

Do not push if either commit failed or there was nothing to commit.

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
- Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
- Never use `cd` before git commands. Use `git -C /absolute/path <command>`.
- Name every path in the commit pathspec (step 8). Never `git add -A`, never `git commit -a`. **Exception - mass deletion/move of tracked files:** when a commit's whole purpose is deleting or moving many tracked files (e.g. a framework rewrite wiping an old tree), naming each path is impractical; pass the containing tree instead - `git commit -m "<message>" -- <tree-path>` - never a bare repo-wide pathspec (which would also sweep in any unrelated uncommitted edits sitting elsewhere in the repo). A pathspec only picks up already-tracked files, never untracked ones, so it stays within the "know what you're committing" intent while `-A` does not. Sanity-check `git status` after, and if the deletion set is mixed with unrelated edits, split them.

## Edge cases: merges, partial staging, backdating

Rare paths, read on demand: `skills/commit/edge-cases.md` covers merge-commit resolution, splitting one file's changes across separate commits (partial staging), and backdating commit timestamps.

## Grouping: shared-component swaps

When a file's only change is swapping a local implementation for a shared / design-system component, it belongs with the commit that adds or changes that shared component - not the feature commit that happened to trigger the swap. If that file also carries feature-specific edits, split it via partial staging (`skills/commit/edge-cases.md`): swap hunks go with the component commit, the rest with the feature.
