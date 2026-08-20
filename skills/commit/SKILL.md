---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, pushbump, pushnbump, fold) to commit changes.
argument-hint: "[v|bump|push|pushbump|pushnbump|onlyv|onlybump|fold <sha>]"
---

# /commit

> Commit changes into clean, well-organized commits.

## `/commit`

**Commit-guard marker:** a global PreToolUse hook blocks raw `git commit`. Before the FIRST `git commit` call of a session, write a session marker, in its OWN tool call, never chained with the commit (`;`/`&&`) - the hook inspects the whole command string BEFORE any of it runs, so a chained marker does not exist yet at hook time and the call is always rejected whole, nothing in it executes:

Call the helper, never a hand-built path. It owns the directory join and refuses to write a malformed marker rather than producing a stray file (todo 365: two strays reached the tree from hand-built paths, one missing the separator, one with an unexpanded variable):

```powershell
& "C:\Users\tecno\.claude\hooks\write-session-marker.ps1"
```

The marker is keyed to this session and is never consumed, so every later commit in the same session needs no marker write at all - just call `git commit` directly. A raw `git commit` from a session that never wrote this marker is still blocked, and two concurrent sessions can never share or steal each other's marker since each is keyed to its own session id.

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.), including a documented "pre-commit hook reformats beyond the staged diff" note - if present, follow its stated `--no-verify` authorization and size threshold exactly. Absent such a note, never bypass a hook on your own judgment - except the shared-checkout hazard in step 8, which applies regardless of commit-style.md. Only read it once per session.
1a. **Branch-protection check** - convention-driven, not branch-name-driven, so it only fires where a repo has actually opted in. Run `git rev-parse --abbrev-ref HEAD` and record the result as this run's EXPECTED branch (step 8 re-checks against it before every commit). If ALL three hold - the branch matches a protected-trunk name (`main`, `master`, `develop`, or a project override), the repo has a remote (`git remote` is non-empty), and a `GIT_FLOW.md` (or an equivalent documented trunk-protection rule in root `CLAUDE.md`) exists at the repo root - stop and ask via `AskUserQuestion`: branch first, commit anyway (explicit override), or abort. Repos with no such documented convention are unaffected, protected-sounding branch name or not - this explicitly does NOT fire on `~/.claude` itself, which commits to `master` by design and has no `GIT_FLOW.md`.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Comment-noise, em-dash, and secret-scan check** (always runs, no size/skip-review gate - unlike `/close`'s conditional `/code-check` pass, this fires on every commit, no exception for a small diff). Run all three in one shot via `skills/commit/prefilter-gate.sh`, replacing `<files>` with the paths this commit will touch, including not-yet-`git add`ed new files - each wrapped script's untracked-file pass is what makes those visible, since a bare `git diff HEAD` cannot see them:

    ```
    bash skills/commit/prefilter-gate.sh <files>
    ```

    Exit 0 = all three clean, continue. Non-zero exit = at least one prefilter flagged something; its output is printed labeled by script (`=== comment-noise.sh ===`, etc). The wrapper only decides pass/fail - read the labeled section(s) and apply the matching per-script treatment before retrying: comment-noise flagged = trim the offending blocks now - per the cap in `skills/commit/comment-noise.md` (2 lines typical, 4 hard per block, 25% ratio once a file adds 20+ lines) - before committing, don't ask, matching `/create-pr` step 2b's auto-trim. **Exception:** a block flagged only because it moved verbatim from elsewhere in this same commit is not new noise - confirm via `git show HEAD:<old-file>` before trimming it, see comment-noise.md's judge step. Em-dash flagged = fix that added line now, same don't-ask treatment; the script only looks at added lines, so a pre-existing em dash on an unchanged line never gets reported and needs no exception. **Secret-scan flagged = STOP, do not auto-fix.** This is the one prefilter in this step that is not a "trim it and continue" call - a hardcoded credential needs a human decision, not a silent edit. Remove the literal value, replace it with an env var or secret-store read, then re-run the gate before committing; see `skills/commit/secret-scan.md` for what it matches and why a hit is never auto-resolved. `comment-noise.md`/`comment-noise.sh`/`em-dash.sh`/`secret-scan.md`/`secret-scan.sh` stay the one place the cap number and each prefilter's own logic are defined; `prefilter-gate.sh` just runs the three and turns "printed anything" into a real exit code, and still works standalone for other skills that call an individual script directly.
6. Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait for the result. If it fails, **abort the commit**, print the failing output, and explain to the user exactly why the commit was aborted (which command failed, what it printed, and that they need to fix it or tell you to skip). Do not stage or commit anything until the user either fixes it or explicitly says to skip.
6a. **No `run-tests` skill found - detect an obvious suite before concluding there's nothing to run.** Mechanical checks only, no guessing, excluding `node_modules`/`.git`/vendor dirs:
   - **A `ci/run_all.py` at the repo root: run `python ci/run_all.py` and treat its verdict as the whole suite, then skip the remaining bullets.** It composes that repo's own mechanical checks and already covers the per-file Python pass below. In `~/.claude` that means the 13 `hooks/test_*.py` self-test suites, skill-frontmatter validation across all 83 skills, and the always-loaded instruction token budget; the same workflow runs in GitHub Actions via `.github/workflows/ci.yml`, so a local pass and a green CI run mean the same thing.
   - Python: any `test_*.py` or `*_test.py` files anywhere in the repo (`Get-ChildItem -Recurse -Filter "test_*.py"`, plus `*_test.py`). If found, run each with `python <file>`.
   - Node: a root `package.json` with a `"test"` script. If found, run the project's package manager `test` command.
   - A `tests/` directory containing a runner config (`pytest.ini`, `jest.config.*`, etc). If found, run the matching runner.
   Apply step 6's own failure treatment: any non-zero exit **aborts the commit**, prints the failing output, and explains what to fix - same as a `run-tests` skill failing. If none of these are found, say so explicitly ("no test suite detected") rather than passing silently. Slow e2e suites (Playwright, etc) are out of scope here - those stay opt-in per the floor in `CLAUDE.md`.
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
8. **Commit by pathspec, never stage-then-commit.** Five preconditions, checked right here, not skimmed past earlier - all required, every single commit, not once per run:
   - Have step 5a's prefilter gate actually been run against this exact pathspec, this turn, and exited 0 (or been rerun clean after trimming)? If not, stop and run it now - do not call `git commit` first and rationalize the check afterward. Chain the two in one line so a flagged diff structurally cannot reach the commit: `bash skills/commit/prefilter-gate.sh <files> && git commit -m "<message>" -- <files>` - a non-zero exit stops the `&&` before `git commit` ever runs, closing the gap where a prior session ran both in one shell call and the commit landed before the flagged output was read (todo 356).
   - **Step 1 re-check:** if `.claude/commit-style.md` exists in this repo and hasn't actually been read this session (not "probably was"), read it now before continuing.
   - **Branch guard:** run `git rev-parse --abbrev-ref HEAD` again, right now - not the value step 1a recorded minutes ago. If it differs from step 1a's EXPECTED branch, or prints `HEAD` (detached), STOP: do not commit, and surface both branch names to the dev. A pathspec commit protects the INDEX from a concurrent session's staged files; it says nothing about which BRANCH receives the commit, and a multi-commit sweep leaves plenty of time for another session sharing this checkout to move HEAD underneath it.
   - **Unpushed-overlap check (hunk-level, not file-level - see todo 368):** `git log @{u}..HEAD --format='%h'` (skip silently, no upstream). For each sha, `git show --name-only --format= <sha>` and intersect with this commit's pathspec - this file-level pass is only a cheap pre-filter, not the verdict, since a long-lived repo's frequently-touched files (`CLAUDE.md`, any SKILL.md, `.gitignore`) will file-match nearly every unpushed sha without ever sharing a line. For each file that survives the pre-filter: run `git diff -- <file>` (the pending change about to be committed) and read each hunk's OLD-side range from its `@@ -a,b +c,d @@` header, skipping any hunk with `b=0` (pure addition - new lines can't overlap prior work). For each surviving range, run `git blame -L a,a+b-1 HEAD -- <file>` and collect the shas it reports. Only a match between a blamed sha and one of the file-level candidate shas is a real hit. A file-level candidate with no blamed-sha match is NOT a hit - state it in one line (file, unrelated commit, no shared lines) and proceed without asking; that is the common, expected case here and is exactly the noise todo 368 removed. On a real hunk-level hit: **interactive session** - STOP, name the overlapping commit and the blamed lines, ask via `AskUserQuestion` whether this is follow-up on the same unit of work (-> `git reset --soft HEAD~1`, restage everything together, one fresh commit) or genuinely separate (-> proceed). **Unattended run** (`/auto-do-todos`, `/autopilot`, or any caller that cannot block on a question) - there is no one to ask, so take the genuinely-separate branch and proceed, but record the overlapping commit, file, and blamed lines in that run's own summary/report-back; a human reviews it after the fact instead of blocking the run. This is the one place that unattended-hit behavior is defined - it is not restated in the runner skills themselves.
   - **Working-tree diff check (the working-tree half of the shared-checkout risk; the unpushed-overlap check above is the index/history half - see todo 218's lineage, this does not re-solve that side):** run `git diff -- <every pathspec entry>` immediately before `git commit`. Account for every hunk shown. An unrecognised hunk - one you did not write this session - is a STOP: either drop that path from the pathspec, or announce on the repo channel that you are taking the file whole and name whose lines ride along. Never assume a dirty file named in your pathspec is dirty only because of you; a pathspec commit takes the file's entire working-tree state, and `git status`'s one `M` line cannot tell you whose lines are in it.

   **Shared-checkout hook hazard:** if this repo has a pre-commit hook configured (`git config core.hooksPath`) and is a shared `.git` checkout (`git rev-parse --git-common-dir` differs from `--git-dir`, or `.git/index.lock` exists) - add `--no-verify` below and run the project's formatter/linter by hand first. A hook that stages, stashes, or hides files is a WORKING-TREE risk that pathspec commits do not cover. Full reasoning and recovery: `skills/commit/edge-cases.md`.

   Then run `git commit -m "<message>" -- <file> <file> ...`, naming every path this commit should contain. This commits exactly those paths' current working-tree state and never reads the index, so it is correct whether or not a concurrent session sharing this repo's `.git/index` has its own work staged there. No shared-index check is needed and none should be run - the form is unconditional.
   - **Multiline message, or one containing a literal `"`:** in PowerShell, a `-m` value passed to `git.exe` (a native command) that contains an embedded `"` gets mis-tokenized during argument marshalling and silently word-splits, regardless of whether it's inlined via `-m @'...'@` or built first as `$msg = @'...'@; git commit -m $msg` - proven 2026-08-19, both forms fail identically with `"` present and both succeed once it's gone, so the variable assignment is not what matters. The actual fix: escape every literal `"` in the message content as `\"` before it reaches `-m`, in either form. `git` unescapes it back to a plain `"` in the stored message.
   - **Immediately after that commit succeeds, run `git rev-parse --short HEAD` as its own call.** THAT value is what gets reported to the dev or recorded anywhere - never a sha read from the commit command's own output (routinely truncated by output filters like `| tail`) and never one recalled from memory.
   - **Untracked files are the one exception:** a pathspec cannot name a file git doesn't know yet, so `git add <new-file> <new-file>` them first, then include them in the same pathspec commit. That add only ever touches your own paths.
   - Never `git reset` or unstage entries you didn't stage - that disrupts another session's commit prep. **Exception:** the unpushed-overlap check above, which is a deliberate, surfaced `reset --soft` on your own prior commit, never someone else's.
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

## `/commit fold <sha>`

Folds newly-staged-or-named fixes into an existing commit `<sha>` that is not yet pushed, preserving every other commit's original message, author, and timestamp. This is the explicit, dev-named counterpart to `~/.claude/snippets/auto-commit.md`'s "Folding a correction into the last commit" section, not a replacement for it - if `<sha>` is HEAD and nothing has landed on top of it since, that snippet's own atomic `update-ref` recipe (its Case A) is simpler and applies directly, use it instead. This mode exists for the case that snippet marks unsafe for silent/automatic action (its Case B, other commits sitting on top of the target) but which is fine once a dev explicitly names the sha and no file overlap blocks a clean split.

**Preconditions, checked in this order, before anything is written:**

1. Resolve `<sha>` to a full hash (`git rev-parse <sha>`). Unresolvable: stop, tell the dev.
2. **Pushed check, unmissable.** `git rev-parse --abbrev-ref --symbolic-full-name @{u}` for the upstream.
   - No upstream configured: nothing to push to yet, so `<sha>` cannot be "already pushed" - safe on this axis, continue.
   - Upstream exists: `git branch -r --contains <sha>`. Any output means `<sha>` is reachable from a remote branch - **refuse**, name the sha, and tell the dev to make a normal follow-up `FIX:` commit instead (same fix-forward wording as auto-commit.md's "Fixes: `<short-sha>`" body line). Stop, do not touch history.
3. **Overlap check.** `git log --format=%H <sha>..HEAD` lists every commit on top of the target. For each, `git show --name-only --format= <commit>` and intersect with the file list this fold is about to touch. Any overlap: a clean pathspec split can't separate the hunks - **refuse this mode**, point the dev at "Splitting one file across commits" in `skills/commit/edge-cases.md` instead.
4. Step 5a's `prefilter-gate.sh` runs against the fold's own file set, same as any other commit.
5. Branch guard: record `git rev-parse --abbrev-ref HEAD` now, and re-check it immediately before the reset below - same rule as step 8's, stop if it moved. Same peer check (7a) too: announce the pathspec about to be rewritten before touching history.

**Recipe, once every precondition passes:**

1. Record the ordered commit list from `<sha>` to `HEAD`, oldest first, with each full hash, author date, committer date, and message: `git log --format='%H|%aI|%cI|%s' --reverse <sha>~1..HEAD`.
2. `git reset --soft <sha>~1` - moves HEAD to the target's parent; the index now holds everything from `<sha>..HEAD` plus this fold's own fix, together. Same deliberate, surfaced exception to the "never reset what you didn't stage" rule as step 8's own unpushed-overlap check - this is the dev's own prior work, named explicitly.
3. Recommit oldest first by pathspec, never `git add -A`:
   - First commit = the original target's own file list plus the fold's fix files, using the **original** message from step 1, with `--date` and `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` set to the original timestamps.
   - Each remaining original commit, in original order, recommitted with its own unchanged file list, original message, original timestamps.
4. **Verify via patch-diff, not full-tree-diff**, every commit except the folded one: `git show <original-sha>` must diff empty against `git show <new-sha>` for its replacement. A full-tree comparison would not catch a hunk silently landing in the wrong commit.
5. Report the old-sha to new-sha remapping to the dev.

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
