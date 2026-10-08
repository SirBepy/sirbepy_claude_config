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
1a. **Branch-protection check** - convention-driven, not branch-name-driven, so it only fires where a repo has actually opted in. Run `git rev-parse --abbrev-ref HEAD` and record the result as this run's EXPECTED branch, and `git rev-parse HEAD` as this run's EXPECTED sha (step 8 re-checks both against it before every commit - the sha catches a peer commit that landed on the SAME branch, which a branch-name-only check would miss). Also start this run's OWN-COMMIT list empty and its overlap queue empty (step 8 appends to both - todo 860). These two are per-run; two more are session-scoped and survive across separate `/commit` invocations in the same session, so only initialize them if this is the session's first invocation: this session's cumulative own-commit list (every sha this session has committed, appended alongside the per-run list at step 8's post-commit line), and this session's fold-policy, unset until step 8's end-of-queue question is first answered (todo 862). If ALL three hold - the branch matches a protected-trunk name (`main`, `master`, `develop`, or a project override), the repo has a remote (`git remote` is non-empty), and a `GIT_FLOW.md` (or an equivalent documented trunk-protection rule in root `CLAUDE.md`) exists at the repo root - stop and ask via `AskUserQuestion`: branch first, commit anyway (explicit override), or abort. Repos with no such documented convention are unaffected, protected-sounding branch name or not - this explicitly does NOT fire on `~/.claude` itself, which commits to `master` by design and has no `GIT_FLOW.md`.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Em-dash, secret-scan, and comment-tense check** (always runs, no size/skip-review gate - unlike `/close`'s conditional `/code-check` pass, this fires on every commit, no exception for a small diff). Run everything in one shot via `skills/commit/prefilter-gate.sh`, replacing `<files>` with the paths this commit will touch, including not-yet-`git add`ed new files - each wrapped script's untracked-file pass is what makes those visible, since a bare `git diff HEAD` cannot see them. Example assumes cwd is the target repo root (`~/.claude` below); from elsewhere, either `cd` there first or pass an absolute path - the gate resolves EACH path's own repo independently, so a mix of parent-repo and submodule paths in one call is fine, no `-C`/`--repo` flag needed for that case (todo 447, todo 412):

    ```
    bash ~/.claude/skills/commit/prefilter-gate.sh <files>
    ```

    Exit 0 = clean, continue. Exit 1 = comment-tense, em-dash, or secret-scan flagged something; its output is printed labeled by script (`=== em-dash.sh ===`, etc). **Exit 2 = the gate itself could not run** (bad path, or no git repo found for the given path) - a single plain-English `ERROR:` line, never raw `fatal:` git output; fix the path/cwd and rerun, this is not a finding to act on. Read the labeled section(s) and apply the matching per-script treatment before retrying: em-dash flagged = fix that added line now, don't ask; the script only looks at added lines, so a pre-existing em dash on an unchanged line never gets reported and needs no exception. Todo-ref flagged (`todo-ref.sh`: an added code comment citing a backlog todo by number, e.g. "todo 44") = drop the number and keep the reason, same don't-ask treatment. Comment-tense flagged = rewrite the flagged comment to state what the code IS, never what changed about it, same don't-ask treatment. **Secret-scan flagged = STOP, do not auto-fix.** This is the one prefilter in this step that is not a "fix it and continue" call - a hardcoded credential needs a human decision, not a silent edit. Remove the literal value, replace it with an env var or secret-store read, then re-run the gate before committing; see `skills/commit/secret-scan.md` for what it matches and why a hit is never auto-resolved. `comment-tense.md`/`comment-tense.sh`/`em-dash.sh`/`secret-scan.md`/`secret-scan.sh` stay the one place each prefilter's own logic is defined; `prefilter-gate.sh` just runs them and turns "printed anything" into a real exit code, and still works standalone for other skills that call an individual script directly.
6. Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait for the result. If it fails, do not abort on the raw exit code alone - a failure that already existed before this change is not this change's fault to fix. Run the **baseline comparison** below before deciding.

   **Baseline comparison (applies to this step and 6a alike):** compare failing-test IDENTITY, never a raw pass/fail count - a test file that errors at COLLECT time reports zero tests and zero failures, so a count-based check sees `0 == 0` on a suite that is genuinely broken and calls it unchanged.
   - Build the CURRENT failing set from the run just done: one entry per failing test (`<file>::<test name>`, or whatever unique id the runner prints), plus one entry per file that failed to collect / errored before any test ran, keyed by file path alone - a collect-time error is a failure, never an absence of tests.
   - Build the BASELINE failing set the same way, but against `HEAD` instead of the working tree: `git worktree add --detach <tmp-dir> HEAD`, run the identical test command inside `<tmp-dir>`, extract the same identity set, then remove it. If the harness moved this session's primary cwd into `<tmp-dir>` (it does this automatically on `worktree add`), move the process cwd back out first with `[System.IO.Directory]::SetCurrentDirectory('<repo root>')` in the same PowerShell call - a plain `Set-Location` does not change the OS cwd a directory handle is held against, and removal fails with "Permission denied" while that handle is still open (todo 1079). Then remove via `~/.claude/skills/close/safe-remove-worktree.ps1 -WorktreePath <tmp-dir> -RepoRoot <repo root>`, never a bare `git worktree remove --force`, matching `refs/builder-preamble.md`. Never `git stash` for this - a shared checkout may hold another session's own uncommitted work in the same tree.
   - CURRENT is a subset of BASELINE (every current failure already existed at `HEAD`): nothing this change touched got worse. Proceed, but record both identity sets (or their diff) as evidence in the commit report / run summary - required, not optional. No question needed, attended or unattended.
   - CURRENT has a member not in BASELINE (a genuinely new failure): **abort the commit**, print the failing output, and name the new failure(s) specifically. Attended session: do not stage or commit until the dev fixes it or explicitly says to skip. Unattended run (`/mega-todos`, `/auto-do-todos`, or any caller that cannot block on a question): there is no one to ask, so abort unconditionally and record the new failure's identity in that run's own summary instead of pausing for input.
6a. **No `run-tests` skill found - detect an obvious suite before concluding there's nothing to run.** Mechanical checks only, no guessing, excluding `node_modules`/`.git`/vendor dirs:
   - **A `ci/run_all.py` at the repo root: run `python ci/run_all.py` and treat its verdict as the whole suite, then skip the remaining bullets.** It composes that repo's own mechanical checks and already covers the per-file Python pass below. In `~/.claude` that means every `hooks/test_*.py` self-test suite, skill-frontmatter validation across all 83 skills, and the always-loaded instruction token budget; the same workflow runs in GitHub Actions via `.github/workflows/ci.yml`, so a local pass and a green CI run mean the same thing.
   - Python: any `test_*.py` or `*_test.py` files anywhere in the repo (`Get-ChildItem -Recurse -Filter "test_*.py"`, plus `*_test.py`). If found, run each with `python <file>`.
   - Node: a root `package.json` with a `"test"` script. If found, run the project's package manager `test` command.
   - A `tests/` directory containing a runner config (`pytest.ini`, `jest.config.*`, etc). If found, run the matching runner.
   Apply step 6's own baseline comparison and failure treatment to whichever runner matched above - same identity comparison, same required evidence, same unattended-aborts-without-asking rule. If none of these are found, say so explicitly ("no test suite detected") rather than passing silently. Slow e2e suites (Playwright, etc) are out of scope here - those run once per push, in the Pre-push gate.
6b. **Fast-check and test-coverage gate** - every repo, per the floor in `CLAUDE.md`.
   - **`/test`** runs in place of step 6a's detection, since it also covers typecheck, lint and build. Step 6's baseline comparison applies to its failures unchanged. A repo with a project `run-tests` skill (step 6) still runs `/test` afterwards for the checks that skill does not cover.
   - **Test coverage check:** `commit-pathspec.sh` now enforces this mechanically (`[coverage-tests-check]`, todo 1045) - if the pathspec changes non-test source files and touches no test file, it refuses by default. A test file is recognized by basename (`test_*`/`*_test.*`/`*.test.*`/`*.spec.*`/`*-probe.*`/`*-unit.*`) or path segment (`test`/`tests`/`__tests__`/`spec`/`verify`) (todo 1138). Write the test that fails without the change, or rerun with `--force coverage-tests` and state in the commit report why the change is untestable by Claude. In a repo listed in `refs/local-only-tests.txt` (tests never committed there), an untracked test file in the pathspec is refused outright and never overridable - add it to `.git/info/exclude` instead - and the "no test file in the pathspec" pass condition becomes "an untracked/ignored test-path file was modified somewhere in the repo within the last 24h" (todo 1138).
   - `/code-check` does not run here; it runs once per push, in the Pre-push gate.
7. **Submodule check:** run `git submodule status` (no flags). For each submodule whose sha is prefixed with `+` (modified) or `-` (uninitialized/not checked out), handle it before committing the parent:
   - If prefixed with `-`: warn the user, do not auto-commit an uninitialized submodule.
   - If prefixed with `+` (dirty pointer: submodule has new commits not yet staged in parent): this is fine, include `<submodule-path>` in step 8's commit pathspec and the pointer bump lands with the parent commit.
   - If the submodule itself has **uncommitted working-tree changes** (detected via `git -C <submodule-path> status --porcelain`): run the 4-step submodule commit flow first:
     1. `git -C <submodule-path> add <changed files by name>` - stage changed files inside the submodule.
     2. `git -C <submodule-path> commit -m "<message>"` - commit inside the submodule using the same prefix/style rules as the parent commit.
     3. Include `<submodule-path>` in step 8's commit pathspec - a gitlink path commits the submodule's current HEAD, so no `git add` is needed in the parent.
     4. Then continue to step 8 as normal; the parent commit will include the pointer bump.
   - If no submodules or all are clean: skip this step silently.
7a. **Peer check:** call `read_messages` first, every commit, whether or not `list_peers` shows anyone (it has returned a false empty list before, and a peer that already closed can still have left a message). If an unread message addresses this session, or names a file in the pathspec, the feature being committed, or says stop / hold / don't commit or ship, act on it before going on: proceed only if it is clearly unrelated or already superseded, otherwise narrow the pathspec or stop and ask. A peer told this session three times not to commit a refused change, and it committed and published anyway because nothing here read the channel (todo 1127). Then call `list_peers`; if it shows another active session in this repo, call `post_message` naming the pathspec about to be committed, then proceed - this applies even inside a dedicated worktree, since collisions happen at merge time, not on disk. The same `read_messages` check runs again right before `git push` and before any deploy-style step that follows a commit (an upload to live, a publish). All three are MCP tools that may not exist in a plain terminal session; if one is unavailable, skip that call silently.
8. **Commit by pathspec, never stage-then-commit.** Five preconditions, checked right here, not skimmed past earlier - all required, every single commit, not once per run:
   - Have step 5a's prefilter gate actually been run against this exact pathspec, this turn, and exited 0 (or been rerun clean after trimming)? If not, stop and run it now - do not call `git commit` first and rationalize the check afterward. Chain the two in one line so a flagged diff structurally cannot reach the commit: `bash ~/.claude/skills/commit/prefilter-gate.sh <files> && git commit -m "<message>" -- <files>` (absolute script path, same reason as step 5a: a repo-relative one only resolves when cwd happens to be `~/.claude`) - a non-zero exit stops the `&&` before `git commit` ever runs, closing the gap where a prior session ran both in one shell call and the commit landed before the flagged output was read (todo 356). Still required even though the commit-guard hook now re-runs this same gate itself against the commit's own `-- <files>` pathspec at commit time (todo 844) - that backstop exists for a `;` that ignores exit status, not as a reason to skip running the gate yourself first. **Decided gap (todo 868):** a commit issued with no `-- <files>` pathspec at all is not covered by that backstop either, and this is accepted, not pending - the hook would have to read the shared index to guess an intended pathspec, and trusting that index's content is worse than the gap it would close. It only bites a caller that has already broken this step's own "always name the pathspec" rule.
   - **Step 1 re-check:** if `.claude/commit-style.md` exists in this repo and hasn't actually been read this session (not "probably was"), read it now before continuing.
   - **Branch guard:** run `git rev-parse --abbrev-ref HEAD` again, right now - not the value step 1a recorded minutes ago. If it differs from step 1a's EXPECTED branch, or prints `HEAD` (detached), STOP: do not commit, and surface both branch names to the dev. A pathspec commit protects the INDEX from a concurrent session's staged files; it says nothing about which BRANCH receives the commit, and a multi-commit sweep leaves plenty of time for another session sharing this checkout to move HEAD underneath it.
   - **HEAD guard (todo 895):** also run `git rev-parse HEAD` right now and compare it to step 1a's EXPECTED sha. A mismatch on the SAME branch means a commit landed here since this run started - a peer, detected from git alone, regardless of what step 7a's `list_peers` reported (it has returned a false "no peers" empty result before). On a mismatch, pick one before committing: announce it on the repo channel via `post_message` and proceed, narrow this commit's pathspec to avoid any file the new commit touched and proceed, or stop and ask if the overlap is unclear.
   - **Unpushed-overlap check (hunk-level, not file-level - see todo 368, script per todo 474, own/foreign split per todo 860):** `bash ~/.claude/skills/commit/overlap-check.sh -C <repo> --own <this run's OWN-COMMIT list, comma-joined full shas> <files>` (absolute path; same pathspec as this commit; omit `--own` while that list is still empty).

     **Runtime:** scales with pathspec size times unpushed-commit depth - whenever the pathspec exceeds roughly a dozen files, give this call an explicit `timeout` (up to 600000ms); the Bash tool's 120s default otherwise auto-backgrounds it, and a backgrounded gate is an unrun gate that must complete before `git commit` runs.

     **What the script owns:** the algorithm end to end - file-level pre-filter against `@{u}..HEAD`, then per-file hunk-range blame, comparing full 40-char shas throughout so a candidate sha can never be silently missed by width or a boundary-commit `^` marker. Any `--own` sha prints as info only and never sets exit 1: a deep unpushed stack overlapping its own earlier commits from this same run is the structural, expected case, not the risk the check exists for.

     **Exit codes:**
     - `0` = clean: no upstream, or every candidate own or line-disjoint (each printed as its own one-line info) - proceed without asking.
     - `2` = the script could not run - a plain-English `ERROR:` line, fix the path/repo and rerun, not a finding to act on.
     - `1` = a real hunk-level hit against a commit this run did NOT itself make, printed as `<file>:<range> <sha> <subject>` - the decision on a hit is policy, not algorithm, and lives here only.

     **On exit 1, evaluate in this order** - this is the order the checks are made in, and it matters: the commit-style ruling-out check runs before anything else does.

     1. **Cross-ticket sharing is forbidden (todo 849).** Check whether the repo's `.claude/commit-style.md` (already read in step 1) forbids sharing a commit across tickets or units of work, and whether the blamed commit belongs to a different ticket than this one. If both hold, that rules out every fold on this hit: skip `AskUserQuestion` entirely, take the genuinely-separate branch, and print one line naming the overlapping commit, the blamed lines, and the quoted rule that ruled out the fold.
     2. **Personal repo - never ask (todo 941).** `python ~/.claude/hooks/_client_repo.py is-client <repo>` reports `personal` (the repo is not in `refs/client-repos.txt`, whoever owns it, including a repo with no remote) - the same client list `/cleanup-todos`'s worth rubric and the Pre-push gate use (todo 1045). Take the genuinely-separate branch, print one line naming the overlapping commit and its blamed lines exactly as branch 5 below does, and skip the rest of this list's queue-and-ask machinery entirely. Standing dev instruction, 2026-09-05: "we never have to fold, we can always just commit" - an extra commit on a solo repo costs nothing, so the ask has no upside, and this check had already been narrowed four separate times (todos 368, 474, 498, 500) to fire less often without anyone asking whether it should fire on a solo repo at all. `/commit fold <sha>` typed by the dev himself is unaffected.
     3. **Client repo, interactive session - queue, then ask once at end-of-queue.** Do not stop here. Append the commit, file and blamed lines to this run's overlap queue (step 1a), take the genuinely-separate branch, and continue to the commit below. When this run has no further commit pending (a single-commit invocation, or the last commit of a multi-commit sweep) and the queue is non-empty: check branch 4 first. If it does not apply, ask ONE `AskUserQuestion` naming every queued commit and its blamed lines, offering `/commit fold <sha>` per item or proceed-as-is for all - never one question per commit - and record the answer as this session's fold-policy so later invocations can reuse it.
     4. **A recorded fold-policy already covers every queued item - reuse it, don't re-ask (todo 862).** Applies instead of branch 3's ask, checked at the same end-of-queue moment: if this session already holds a fold-policy (step 1a) AND every queued item is covered by it - none is blamed on the literal current HEAD, and none names a commit from this session's cumulative own-commit list that the recorded policy did not already see - apply the policy to each queued item without asking, and state in the commit report which commits it was applied to and that this is a session-scoped reuse, not a fresh answer. Exception: a blamed commit that IS the literal current HEAD, or that this session made itself, always gets a fresh ask regardless of any recorded policy - it is the "same unit of work" case the policy was never asked about.
     5. **Unattended run - never ask, record in the run summary.** `/auto-do-todos`, `/autopilot`, or any caller that cannot block on a question: there is no one to ask, so take the genuinely-separate branch and proceed, but record the overlapping commit, file, and blamed lines in that run's own summary/report-back; a human reviews it after the fact instead of blocking the run. This is the one place that unattended-hit behavior is defined - it is not restated in the runner skills themselves.
   - **Working-tree diff check (the working-tree half of the shared-checkout risk; the unpushed-overlap check above is the index/history half - see todo 218's lineage, this does not re-solve that side):** run `bash ~/.claude/skills/commit/foreign-hunk-check.sh -C <repo> --own <file>:<a>-<b>[,<a>-<b>...] <files>` immediately before `git commit` - one `--own` per pathspec file, giving the new-file line ranges (matching `git diff`'s `+` side) this session actually edited in it, recalled the same way step 1a's own-commit list already is. This mechanizes the account-for-every-hunk read instead of requiring a per-file diff eyeball. Exit 0 = clean, proceed. Exit 2 = the script could not run - fix and rerun, not a finding. Exit 1 = `foreign-hunks-present <range>` (a separate `@@` hunk - drop that path from the pathspec, or announce on the repo channel that you're taking the file whole and name whose lines ride along) or `foreign-hunks-inside-your-hunk <range>` (a peer's lines sit inside the SAME `@@` hunk as yours - `git apply --cached` cannot split it; the two safe orders are in `skills/commit/edge-cases.md`'s "Foreign hunk inside your own hunk"). Never assume a dirty file named in your pathspec is dirty only because of you; a pathspec commit takes the file's entire working-tree state, and `git status`'s one `M` line cannot tell you whose lines are in it.
   - **Staged-pathspec coverage check (catches a half-committed `git mv` or any relocate script, e.g. `complete-todo.ps1` archiving a todo into `done/`):** run `git diff --cached --name-status` immediately before `git commit`. A `git mv` (or any move) stages TWO paths - an add at the destination and a delete at the source - and naming only the destination in the pathspec commits the copy while the source deletion rides along staged and unreported; `git status` afterward shows a live ` D` for a file that no longer exists on disk. For each staged path NOT named in this commit's pathspec, check whether it shares a directory with a path that IS in the pathspec (the move shape): if so, STOP - widen the pathspec to include it, or state deliberately why it's being left behind. If instead it sits in an unrelated directory (the shared-index shape: another session's own legitimately staged work, the common case in this very repo), warn and name it but do not block - blocking there would brick `/commit` for every concurrent session. Recovery if a half-committed move already landed: this is the self-discovered missing-file case in `snippets/auto-commit.md` ("Self-discovered: a file belongs in the commit you just made") - fold the omitted path in via that section's atomic `update-ref` recipe (Case A), never `git commit --amend`. It only works before anything else lands on top of it, same as that recipe's own safe/unsafe check.

   **Shared-checkout hook hazard:** if this repo has a pre-commit hook configured (`git config core.hooksPath`) and is a shared `.git` checkout (`git rev-parse --git-common-dir` differs from `--git-dir`, or `.git/index.lock` exists) - add `--no-verify` below and run the project's formatter/linter by hand first. A hook that stages, stashes, or hides files is a WORKING-TREE risk that pathspec commits do not cover. Full reasoning and recovery: `skills/commit/edge-cases.md`.

   **The whole chain above is scripted** (todo 964). `bash ~/.claude/skills/commit/commit-pathspec.sh --expect-branch <step 1a's EXPECTED branch> --expect-sha <step 1a's EXPECTED sha> -m "<message>" -- <files>` runs the prefilter gate, branch guard, HEAD guard, overlap-check, foreign-hunk-check, the coverage check, the test-coverage check, the commit and the `rev-parse` in order, deriving `foreign-hunk-check`'s `--own` ranges from `git diff HEAD` itself instead of asking the caller to read `@@` headers by eye, but trusting that derivation only when `hooks/.session-markers/` shows this session alone in the checkout (one live marker or zero) - with 2+ live markers a peer may share the file, so the step refuses with an explicit UNVERIFIED verdict instead of `clean` unless a real `--own-range` is declared or `--force foreign-hunk` is given (todo 924, its REOPENED fix; 933 folded in). A caller-declared `--own-range`, and a brand-new untracked file's derived range, stay trusted regardless of session count. **`--force foreign-hunk` on an UNVERIFIED file is not a bare override** (todo 1124 - a 2026-10-07 incident where it silently took a peer's in-progress README section and test rewrite whole): a file with 2+ auto-derived hunks and no caller `--own-range` is REFUSED even with `--force foreign-hunk` - the override needs a stated per-hunk claim, not a flag. A file with exactly one auto-derived hunk has nothing left to disambiguate, so it proceeds, but prints that hunk's `@@` header and its first changed line under `hunk(s) taken on trust:` first, so the caller sees what it is about to take before it lands. It also excludes a path that's already deleted, whether via `git rm` or a plain working-tree delete, from the two checks that cannot diff it while keeping it in the commit. Repeated `-m` accumulates into subject plus body paragraphs, exactly like `git commit -m A -m B` (todo 1109) - never last-one-wins. A repeatable `--todo <id>` appends that todo's own archive-move paths to the pathspec: `.claude/todos/done/<id>-*.md` when complete-todo.ps1 already moved it there, and `.claude/todos/<id>-*.md` too when git still tracks the source (an untracked, peer-filed todo has no source half to add) - see `skills/close/ai-todos-format.md` for the move this mirrors (todo 1105). It ADVISES, never decides: every judgement branch below refuses by default and needs an explicit `--force <check>` naming which one - the five valid names are `head-guard`, `overlap`, `foreign-hunk`, `coverage` and `coverage-tests` (`overlap-check` is also accepted, matching the bracketed `[overlap-check]` label the script itself prints), comma-joined or repeated per flag for more than one - and the branch guard and the prefilter gate take no override at all. On a personal repo (not in `refs/client-repos.txt`, per branch 2, checked via `_client_repo.py` same as that branch - todo 1045) an overlap hit proceeds on its own with an info line instead of refusing, matching branch 2 below (todo 1076); a client repo (on the list, or `_client_repo.py` failing to run at all - the stricter direction) still refuses by default and names `--force overlap` in its refusal. **Test-coverage check (todo 1045):** if the pathspec changes a non-test source file (the extension list in the script's `is_source_file`, excluding anything under `.claude/todos/`) and touches no test file (`test_*`/`*_test.*`/`*.test.*`/`*.spec.*`/`*-probe.*`/`*-unit.*` by basename, or a `test`/`tests`/`__tests__`/`spec`/`verify` path segment - todo 1138) it is REFUSED as `[coverage-tests-check]`, overridable with `--force coverage-tests`. In a repo listed in `refs/local-only-tests.txt` an untracked test file in the pathspec is refused outright instead, never overridable (add it to `.git/info/exclude`, never the team's `.gitignore`), and the no-test-file pass condition becomes a test-path file outside the index (untracked or ignored) touched somewhere in the repo within the last 24h (todo 1138). The prose below stays the source of truth for what each check MEANS and what a hit implies - the script mechanises the sequence, not the policy, so read it here and run it there. Doing it by hand stays correct and is the fallback if the script is unavailable.

   **Never pipe this script's output** (`| tail`, `| head`, `| grep`, etc.) **and never chain a `git push` after it in the same command** (`&&`) - either one can swallow the script's own non-zero exit and let a refused commit's push ship anyway (todo 1080). Run it unpiped, or with `set -o pipefail` if a filter is unavoidable, and confirm success from its own exit code or the printed `[commit] committed` line before pushing - never from a line surviving a filter.

   Then run `git commit -m "<message>" -- <file> <file> ...`, naming every path this commit should contain. This commits exactly those paths' current working-tree state and never reads the index, so it is correct whether or not a concurrent session sharing this repo's `.git/index` has its own work staged there. No shared-index check is needed and none should be run - the form is unconditional.
   - **Multiline message, or one containing a literal `"`:** in PowerShell, a `-m` value passed to `git.exe` (a native command) that contains an embedded `"` gets mis-tokenized during argument marshalling and silently word-splits, regardless of whether it's inlined via `-m @'...'@` or built first as `$msg = @'...'@; git commit -m $msg` - proven 2026-08-19, both forms fail identically with `"` present and both succeed once it's gone, so the variable assignment is not what matters. The actual fix: escape every literal `"` in the message content as `\"` before it reaches `-m`, in either form. `git` unescapes it back to a plain `"` in the stored message.
   - **Immediately after that commit succeeds, run `git rev-parse HEAD` as its own call and append it to this run's OWN-COMMIT list from step 1a, and to this session's cumulative own-commit list.** The short form (`git rev-parse --short HEAD`) of that same value is what gets reported to the dev or recorded anywhere - never a sha read from the commit command's own output (routinely truncated by output filters like `| tail`) and never one recalled from memory.
   - **Untracked files are the one exception, but don't pre-`git add` them:** `commit-pathspec.sh` stages a brand-new file itself, after its checks run, so include it in the pathspec unstaged - staging it by hand first only flips it from `commit-pathspec.sh`'s untracked classification to live and forfeits the exemption that classification carries (todo 1026). The manual `git add <new-file>` then commit-by-pathspec order is only for the by-hand fallback when the script is unavailable; that add only ever touches your own paths.
   - Never `git reset` or unstage entries you didn't stage - that disrupts another session's commit prep. **Exception:** `/commit fold <sha>`'s own deliberate, surfaced `reset --soft`, run only against a sha named explicitly by the dev, never invoked automatically here.
   - After a multi-commit sweep, sanity-check with `git merge-base --is-ancestor <last-sha> <expected-branch>` to confirm nothing landed off-branch.
8b. **Post-commit index refresh, only if the repo runs `lint-staged` on pre-commit** (check `git config core.hooksPath` and read the resulting `pre-commit` file for a `lint-staged` call). That hook rewrites the just-committed files in place and applies the result into the commit, which leaves their index entries stat-dirty against the rewritten working tree even though `git diff HEAD` is empty. Fix: `git add` the exact paths just committed, and print which ones. Do NOT use `git reset` here - a shared checkout may have another session's work staged, and reset would disrupt it. Do NOT use `git update-index --refresh` either - it only reports "needs update" per file and stops, it doesn't fix anything.

If nothing to commit, say so and stop.

## `/commit v` / `/commit bump`

Same as `/commit` but also bumps the patch version before committing (e.g. 1.0.0 -> 1.0.1).

Version bump procedure:
1. Before bumping, compare the current version across `package.json`, any other root `.json` with a top-level `"version"` field, and `src-tauri/Cargo.toml` if present. If they disagree, the repo is already drifted: bring every one of them to the new version in this same commit, not just whichever file the last `VERSION:` commit happened to touch, and say so in the summary. A run of prior commits that all touched one file is evidence of an unfixed habit, not a per-repo convention this procedure defers to.
2. Find `package.json` in the repo root. If it exists, it is the **source of truth** - read the version from it, increment the patch number, and write it back.
3. Find any other `.json` files in the repo root that contain a top-level `"version"` field (e.g. `tauri.conf.json`, `manifest.json`). Update each one to match the new version. If a Rust crate manifest exists for the app (`src-tauri/Cargo.toml`), it needs the same bump too - see `skills/commit/edge-cases.md` for the lockfile-regen and scope rules.
4. Include all modified version files in step 8's commit pathspec, alongside the other changed files.

Commit message follows the normal style - no need to mention the version bump.

If no `package.json` exists, skip the version step and commit normally.

## Push pipeline

The full ordered sequence for `/commit push`, `/commit pushbump` and `/commit pushnbump`. This list is the ONLY place the whole sequence is enumerated: `CLAUDE.md`, snippets and memories point here instead of restating it, because every restated copy has drifted the moment a step was added (the todo sweep reached this file while two summaries still listed only `/code-check` + `/e2e`). Adding, removing or reordering a push step means editing this list in the same commit. When describing what a push will run, read this list, never a summary of it.

1. **Commit** - steps 1-8 above, including step 6b's gate (`/test` plus the test-coverage check). `pushbump` adds the version bump; `pushnbump` adds kit sync and a separate version commit.
2. **Pre-push todo sweep** - fold small backlog todos sitting in the files the push already touches.
3. **Pre-push transcript check** - stop on any dev message since the last push that was never addressed.
4. **Pre-push gate** - `/code-check` over `@{u}..HEAD`, then `/e2e` (or its no-suite note), then mark HEAD cleared.
5. **`git push`**.
6. **Post-push ticket move** - every ticket the push shipped goes to Testing.
7. **Build watch** - `skills/commit/build-watch.md`.

**Client-repo commit window.** In a client repo (`refs/client-repos.txt`), `hooks/commit-window-guard.py` denies every commit and push (step 8 and step 5 alike, including `commit-pathspec.sh` and `/mega-todos` builders' raw `git commit`) from 23:00 to 10:59 local, unless Joe approved it in this session. On a denial, follow its message: ask Joe, or defer to an 11:00 wake-up. Never route around it, and never shift a timestamp out of the window.

## Pre-push todo sweep

Runs first for `/commit push`, `/commit pushbump`, and `/commit pushnbump`, before the transcript check and pre-push gate below - it can change what the push ships, so both of those must see the final range. Catches a small backlog todo sitting in the exact files the push already touches, while folding it in is still free.

1. Skip silently when the repo has no `.claude/todos/` backlog with open todos. Skip on an unattended run too (nobody to answer step 3), with one line in the run's report saying the sweep was skipped.
2. Dispatch ONE read-only subagent (`model: 'sonnet'`, canonical preamble from `refs/builder-preamble.md` with the `READ-ONLY DISPATCH` opt-out). Hand it the backlog path and `git log --format='%H %s' --name-only @{u}..HEAD`. A todo qualifies only when all three hold: it touches files an unpushed commit already changes, it is EASY by `/batch-todos`'s table, and it is the same concern or ticket as that commit. Todos with a live claim in `.claims/` and PRODUCT todos never qualify. It returns per hit: todo id, target commit sha, files, and one line on why it fits; zero hits is a valid answer, never padded.
3. Zero hits: proceed silently. Otherwise one `ask_user_question` card, `multiSelect`, one option per hit (todo id, target commit subject, why it fits) plus "none, push as is".
4. Per approved todo: claim it per `skills/close/ai-todos-format.md`, implement it, rerun the fast checks, then fold it into its target commit - Case A in `snippets/auto-commit.md` when the target is HEAD, `/commit fold <sha>` otherwise. When the fold path refuses (overlap with a later commit), commit it on top as its own commit instead, never force the fold. Close the todo and release the claim per the contract.

## Pre-push transcript check

Runs only for `/commit push`, `/commit pushbump`, and `/commit pushnbump`, right before the `git push` call in each - never for a plain `/commit` or version-only bump, which stay untaxed. Catches a dev instruction that landed in the transcript but never reached the working context, before the push ships whatever got built on the gap (todo 902: a rejected layout was built, committed, and pushed because a peer relay sat between the dev's correction and the next turn).

1. Resolve the transcript path via `skills/close/SKILL.md`'s "Transcript grounding" recipe (`~/.claude/sessions/*.json` for `sessionId`, then the sanitised-cwd `.jsonl`) - do not re-derive it. `Grep`, never `Read`: transcripts embed full tool payloads and run to megabytes.
2. Reference point: this session's own last successful push, recalled from an earlier push report in this conversation, never re-derived from git. No prior push this session: the transcript's first line.
3. Grep `"type":"user"` lines after that point whose content is text, not a `tool_result`. A `[daemon-meta]` peer relay is not itself a dev turn, but leave it in the scanned range - it is exactly what can sit between two dev turns and bury one, per the incident above.
4. For each dev text turn found, confirm it was addressed: referenced or acted on later in this conversation, or explicitly superseded by a later dev message. A correction, rejection, or preference ("i dont like...", "no, instead...", "wait, actually...") with no visible acknowledgement afterward is unaddressed.
5. No dev turns since the reference point, or all addressed: proceed silently, no added output.
6. Any unaddressed turn: stop before `git push`, quote the message verbatim, and ask whether to address it now or push anyway.

## Pre-push gate

Runs right after the Pre-push transcript check, for the same three push modes, in every repo. `hooks/push-gate.py` blocks the push until this gate clears HEAD, so skipping it only earns a denied `git push`.

1. `/code-check` over what this push ships (`@{u}..HEAD`). Fix findings about lines the push changes, recommit per the fold rules, rerun; findings about untouched code go to the backlog. When the range is a long unpushed stack (a `/loop-todos` or `/autopilot` run, roughly 10+ commits), also run `skills/review-unpushed/SKILL.md`'s per-commit correctness review first: `/code-check` reviews structure, not each commit's logic.
2. `/e2e` against the same range. **No suite** means `/e2e`'s Run-mode table matches only its "anything else" row (no scripted path). Then branch on `python C:/Users/tecno/.claude/hooks/_client_repo.py is-client <repo>`: `client` gets `/e2e`'s drive-it-by-hand fallback, per `snippets/client-repo.md`; `personal` skips e2e without asking and records "e2e: no suite" in the mark reason.
3. All green: `python C:/Users/tecno/.claude/hooks/push-gate.py mark <repo> --reason "<what passed, e.g. code-check + e2e passed, or code-check passed, e2e: no suite>"`, then push. **The `mark` call and `git push` must be separate tool calls, never chained with `&&`/`;`** - same reason the commit-guard marker at the top of this file must be its own call: the hook inspects the whole command string before any of it runs, so a chained `mark && git push` is denied because the mark has not been written yet when the hook checks for it.
4. Either one red or impossible to run: ask the dev through `ask_user_question` whether to push anyway, naming the failure. Yes: mark with `--reason` naming the failure and his approval, then push. No, or an unattended run with nobody to ask: do not push, report the failure.

## Post-push ticket move

Runs right after a successful `git push`, in all three push modes, attended or not. QA works from the board, not the git log, so a pushed fix still sitting in In Progress never reaches the person who tests it next (2026-09-03: eight pushed tickets left in In Progress; 2026-10-05: sc-54701 pushed and left In Progress, then Claude asked Joe where to move it instead of moving it).

1. Collect ticket ids from the subjects of the commits the push shipped (record `@{u}..HEAD` before pushing): `<id>:` prefixes, `sc-<id>`, `[SC-<id>]`, or a Linear key. No ids: skip silently.
2. Infer the tracker from `origin` the way `/ticket` does. Move a ticket only when Joe owns it and it sits before Testing (Backlog, To Do, In Progress, Blocked, PR Review, On hold). Shortcut: GET the story, then PUT only `workflow_state_id` with the Testing state of the story's own workflow (ENG - Core Workflow: `500018257`). Never send `custom_fields`, because PUT replaces them. If the story's workflow has no Testing-equivalent state, skip it and say so. Linear: the team's Testing/review state, same rules.
3. Testing is the ceiling. Never move a ticket to Ready for deploy or Complete: QA promotes it from Testing, and the release skill closes it from there. A ticket already in Testing or later stays where it is, including one QA bounced and that was just re-fixed.
4. Change the state only. Post no comment and draft no QA note unless the dev asks for one.
5. Name the moved ids in the push report, plus each skipped id and why.

## `/commit push`

Same as `/commit` but also runs `git push` after committing, following the **Push pipeline** above in order.

**Push rule:** if the commit step failed, do not push. If there was nothing to commit, don't stop there either - check `git rev-list --count @{u}..HEAD` (if `@{u}` doesn't resolve, say so and offer `git push -u origin <branch>` instead of silently doing nothing). Zero ahead: say "nothing to commit, nothing to push" and stop. One or more ahead: run the **Pre-push todo sweep**, **Pre-push transcript check** and **Pre-push gate** above, then push those existing commits and report how many.

After a successful push, run the **Post-push ticket move**, then the **Build watch** (see `skills/commit/build-watch.md`).

## `/commit pushbump`

Same as `/commit v` but also runs `git push` after committing.

Same push rule as `/commit push` above, including the **Pre-push todo sweep**, **Pre-push transcript check** and **Pre-push gate**.

After a successful push, run the **Post-push ticket move**, then the **Build watch** (see `skills/commit/build-watch.md`).

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
4. Message: `VERSION: <new-version>`, where `<new-version>` is the full version string after bumping. If a build number field (e.g. `"build"` in `package.json` or `tauri.conf.json`) exists alongside the version, append it: `VERSION: 1.0.1+21`.
5. Run the **Pre-push todo sweep**, **Pre-push transcript check** and **Pre-push gate** above, then `git push`.

Do not push if either commit step failed. Otherwise same push rule as `/commit push` above - a clean-tree branch that's still ahead of its upstream still gets pushed, it just won't happen here since the version commit always produces new changes.

After a successful push, run the **Post-push ticket move**, then the **Build watch** - see `skills/commit/build-watch.md` for the full detect/launch/gated-auto-fix procedure (not needed for a plain `/commit`).

## `/commit onlyv` / `/commit onlybump`

Only bumps the patch version. No other changes staged.
Commit message is always: `CHORE: bump to v1.0.1` (with the actual new version).

Version bump procedure: same as `/commit v` above.

If no `package.json` exists, say so and stop.

## `/commit fold <sha>`

Folds newly-staged-or-named fixes into an existing commit `<sha>` that is not yet pushed, preserving every other commit's original message, author, and timestamp. This is the explicit, dev-named counterpart to `~/.claude/snippets/auto-commit.md`'s "Folding a correction into the last commit" section, not a replacement for it - if `<sha>` is HEAD and nothing has landed on top of it since, that snippet's own atomic `update-ref` recipe (its Case A) is simpler and applies directly, use it instead. This mode exists for the case that snippet marks unsafe for silent/automatic action (its Case B, other commits sitting on top of the target) but which is fine once a dev explicitly names the sha and no file overlap blocks a clean split.

**Preconditions, checked in this order, before anything is written:**

1. Resolve `<sha>` to a full hash (`git rev-parse <sha>`). Unresolvable: stop, tell the dev.
2. **Pushed check, unmissable, and it must query the live remote, never local refs.** A pushed commit is never folded, and the dev is not asked to choose: refuse, name the sha, and tell them to make a normal follow-up commit instead (same fix-forward wording as auto-commit.md's "Fixes: `<short-sha>`" body line). Stop, do not touch history.

   `@{u}` and `origin/*` are **not** evidence. A branch can be pushed with an explicit refspec and never get an upstream, and `origin/*` goes stale the moment a fetch fails (Revaire repos fetch as the wrong account and 404 silently), so both routinely report "unpushed" for a commit that is live on the remote and under review. Prove it against the remote itself:

   - `git remote` empty: nothing to push to, genuinely safe, continue.
   - Otherwise `git ls-remote <remote> 'refs/heads/*'` for the live tip shas. For each tip the local object store already has, `git merge-base --is-ancestor <sha> <tip>`; any success means pushed - refuse.
   - A tip whose object is missing locally cannot be tested, so it cannot clear `<sha>` either. If any tip is untestable and none of the testable ones matched, **refuse anyway** and say the check was inconclusive. This mode rewrites published history when it is wrong, so an unprovable answer is treated as pushed.
3. **Overlap check.** `git log --format=%H <sha>..HEAD` lists every commit on top of the target. For each, `git show --name-only --format= <commit>` and intersect with the file list this fold is about to touch. Any overlap: a clean pathspec split can't separate the hunks - **refuse this mode**, point the dev at "Splitting one file across commits" in `skills/commit/edge-cases.md` instead.
4. Step 5a's `prefilter-gate.sh` runs against the fold's own file set, same as any other commit.
5. Branch guard: record `git rev-parse --abbrev-ref HEAD` now, and re-check it immediately before the reset below - same rule as step 8's, stop if it moved. Same peer check (7a) too: announce the pathspec about to be rewritten before touching history.

**Recipe, once every precondition passes:**

1. Record the ordered commit list from `<sha>` to `HEAD`, oldest first, with each full hash, author date, committer date, and message: `git log --format='%H|%aI|%cI|%s' --reverse <sha>~1..HEAD`.
2. `git reset --soft <sha>~1` - moves HEAD to the target's parent; the index now holds everything from `<sha>..HEAD` plus this fold's own fix, together. Same deliberate, surfaced exception to the "never reset what you didn't stage" rule as step 8's own unpushed-overlap check - this is the dev's own prior work, named explicitly.
3. Recommit oldest first by pathspec, never `git add -A`:
   - First commit = the original target's own file list plus the fold's fix files, using the **original** message from step 1, with `--date` and `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` set to the original timestamps.
   - **Shared-file hazard:** a pathspec commit takes the file's CURRENT working-tree state, not that commit's own diff. Before recommitting, intersect every riding commit's `git show --name-only` list against every other's; any file in more than one means each earlier recommit will silently absorb later commits' hunks to that file unless restored first - a silent pass here is worse than an aborted fold. Before each intermediate recommit, `git checkout <original-sha> -- <shared-file>` to put the file back to that commit's own blob; before the final commit, restore the pre-fold tip's state the same way.
   - Each remaining original commit, in original order, recommitted with its own unchanged file list (restored per the hazard above if shared), original message, original timestamps.
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

Rare paths, read on demand: `skills/commit/edge-cases.md` covers merge-commit resolution, splitting one file's changes across separate commits (partial staging, now scripted via `python skills/commit/split-hunks.py stage|commit` - `stage` for solo partial staging, `commit` for a shared-index-safe partial commit), and backdating commit timestamps.

## Grouping: shared-component swaps

When a file's only change is swapping a local implementation for a shared / design-system component, it belongs with the commit that adds or changes that shared component - not the feature commit that happened to trigger the swap. If that file also carries feature-specific edits, split it via partial staging (`skills/commit/edge-cases.md`): swap hunks go with the component commit, the rest with the feature.
