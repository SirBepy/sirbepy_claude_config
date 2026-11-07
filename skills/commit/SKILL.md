---
name: commit
description: Triggers on /commit and its subcommands (v, bump, onlybump, onlyv, push, fold) to commit changes.
argument-hint: "[v|bump|push|onlyv|onlybump|fold <sha>]"
---

# /commit

> Commit changes into clean, well-organized commits.

> Removed: `/commit pushbump` and `/commit pushnbump`. A version bump is `/release`. If invoked with either, stop and tell Joe to use `/release`; never fall back to a plain push.

Sidecars, read on demand (each is a pointer from the step that needs it): `by-hand.md` (step 8 without the script, full reasoning), `baseline.md` (step 6 failures), `push.md` (every push), `fold.md` (`/commit fold`), `edge-cases.md` (merges, partial staging, backdating, branch protection, submodules, hook hazard), `build-watch.md`, `secret-scan.md`, `comment-tense.md`.

## `/commit`

**Commit-guard marker:** a global PreToolUse hook blocks raw `git commit`. Before the FIRST `git commit` call of a session, write a session marker in its OWN tool call, never chained with the commit (`;`/`&&`): the hook inspects the whole command string BEFORE any of it runs, so a chained marker does not exist yet at hook time and the call is rejected whole. Call the helper, never a hand-built path (it owns the directory join and refuses to write a malformed marker):

```powershell
& "C:\Users\tecno\.claude\hooks\write-session-marker.ps1"
```

The marker is keyed to this session and never consumed, so every later commit in the same session needs no marker write. A raw `git commit` from a session that never wrote it is still blocked; concurrent sessions cannot share or steal each other's marker.

1. Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully and let its rules override the defaults below (prefixes, grouping, message format, etc.), including a documented "pre-commit hook reformats beyond the staged diff" note: if present, follow its stated `--no-verify` authorization and size threshold exactly. Absent such a note, never bypass a hook on your own judgment, except the shared-checkout hazard in step 8, which applies regardless of commit-style.md. Read it once per session, and if it exists but was not actually read this session (not "probably"), read it before step 8.
1a. **Run bookkeeping and branch protection.** Run `git rev-parse --abbrev-ref HEAD` (this run's EXPECTED branch) and `git rev-parse HEAD` (EXPECTED sha); step 8 re-checks both before every commit, and the sha catches a peer commit on the SAME branch. Start this run's OWN-COMMIT list and its overlap queue empty. Two more are session-scoped and survive across `/commit` invocations in the same session, so initialise them only on the session's first invocation: the session's cumulative own-commit list (every sha this session committed) and the session's fold-policy (unset until step 8's end-of-queue question is first answered). **Branch protection:** if the branch is a protected-trunk name (`main`, `master`, `develop`, or a project override), the repo has a remote, and a `GIT_FLOW.md` (or an equivalent trunk-protection rule in root `CLAUDE.md`) exists, read `edge-cases.md` "Branch protection" and ask before going on. Repos without that documented convention are unaffected, and `~/.claude` itself (commits to `master` by design, no `GIT_FLOW.md`) is explicitly not covered.
2. Run `git status`
3. Run `git diff` to understand the changes
4. Infer the right commit prefix (see below, or per project overrides)
5. Check if a linter exists - if yes, run it and fix all issues first
5a. **Em-dash, secret-scan, todo-ref and comment-tense check** (always runs, no size/skip-review gate, no exception for a small diff). One shot via the gate, with `<files>` = the paths this commit will touch, including not-yet-`git add`ed new files (each wrapped script's untracked-file pass makes those visible; a bare `git diff HEAD` cannot):

    ```
    bash ~/.claude/skills/commit/prefilter-gate.sh <files>
    ```

    Absolute script path; the gate resolves EACH path's own repo independently, so parent-repo and submodule paths can mix, no `-C`/`--repo` flag. Exit 0 = clean. Exit 1 = a prefilter flagged something; output is labeled by script (`=== em-dash.sh ===`, etc). **Exit 2 = the gate itself could not run** (bad path, no git repo for the path), a single plain `ERROR:` line: fix the path/cwd and rerun, not a finding. Treatments: em-dash flagged = fix that added line now, don't ask (only added lines are checked, so a pre-existing em dash on an unchanged line needs no exception). Todo-ref flagged (an added code comment citing a backlog todo by number, e.g. "todo 44") = drop the number, keep the reason, don't ask. Comment-tense flagged = rewrite the comment to state what the code IS, never what changed, don't ask. **Secret-scan flagged = STOP, do not auto-fix**: remove the literal, replace it with an env var or secret-store read, re-run the gate (`secret-scan.md` says what it matches and why a hit is never auto-resolved).
6. Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait. If it fails, do not abort on the raw exit code alone (a failure that already existed before this change is not this change's to fix): run the **baseline comparison** in `baseline.md` (failing-test IDENTITY against `HEAD`, never a pass/fail count) before deciding. A new failure aborts the commit; an unattended run aborts unconditionally and records the identity; a subset-of-baseline failure proceeds with both identity sets recorded as evidence.
6a. **No `run-tests` skill found - detect an obvious suite before concluding there's nothing to run.** Mechanical checks only, excluding `node_modules`/`.git`/vendor dirs:
   - **A `ci/run_all.py` at the repo root: run `python ci/run_all.py` and treat its verdict as the whole suite, then skip the remaining bullets** - except for a pure-prose pathspec (next bullet). In `~/.claude` it covers every `hooks/test_*.py` suite, skill-frontmatter validation across every skill and the always-loaded instruction token budget; GitHub Actions runs the same workflow.
   - **Pure-prose pathspec in `~/.claude`:** every path is markdown under `skills/` or `refs/` and none is `hooks/`, `tools/`, `ci/`, `CLAUDE.md`, `settings.json`, or any `skills/**/test_*` file or executable script: skip the full `python ci/run_all.py` and run only `python ci/check_skill_frontmatter.py` and `python ci/check_instruction_budget.py`, plus any `test_*` file that names a touched skill or reads a touched file (`Grep` the test files for the path: `skills/release/test_pipeline_order.py` pins `skills/commit/push.md` wording). The full suite still runs at the push gate and in GitHub Actions. A failure in either check on a file outside the pathspec is a peer's uncommitted edit: apply the baseline comparison, do not fix it here. Any executable path in the pathspec means the full suite runs.
   - Python: any `test_*.py` or `*_test.py` in the repo; run each with `python <file>`.
   - Node: a root `package.json` with a `"test"` script; run the project's package manager `test` command.
   - A `tests/` directory with a runner config (`pytest.ini`, `jest.config.*`, etc): run the matching runner.
   Step 6's baseline comparison, evidence and unattended-aborts rule apply to whichever matched. If none: say "no test suite detected" explicitly. Slow e2e suites are out of scope here (once per push, in the Pre-push gate).
6b. **Fast-check and test-coverage gate** - every repo, per the floor in `CLAUDE.md`.
   - **`/test`** runs in place of step 6a's detection (it also covers typecheck, lint and build); step 6's baseline comparison applies to its failures. A repo with a `run-tests` skill still runs `/test` afterwards for what that skill does not cover.
   - **Test coverage check:** `commit-pathspec.sh` enforces it (`[coverage-tests-check]`): if the pathspec changes non-test source files and touches no test file, it refuses. A test file is recognised by basename (`test_*`/`*_test.*`/`*.test.*`/`*.spec.*`/`*-probe.*`/`*-unit.*`) or path segment (`test`/`tests`/`__tests__`/`spec`/`verify`); a `.rs` file whose own content has a line-anchored `#[cfg(test)]` block covers itself. Write the test that fails without the change, or rerun with `--force coverage-tests` and state in the commit report why the change is untestable by Claude. In a repo listed in `refs/local-only-tests.txt` (tests never committed there), an untracked test file in the pathspec is refused outright and never overridable (add it to `.git/info/exclude` instead), and the "no test file in the pathspec" pass condition becomes "an untracked/ignored test-path file was modified somewhere in the repo within the last 24h".
   - `/code-check` does not run here; it runs once per push, in the Pre-push gate.
7. **Submodule check:** run `git submodule status` (no flags). `-` prefix (uninitialized): warn the user, never auto-commit it. `+` prefix (new commits not yet staged in the parent): fine, include `<submodule-path>` in step 8's pathspec. Uncommitted working-tree changes inside it (`git -C <submodule-path> status --porcelain`): follow `edge-cases.md` "Submodule check" (commit inside the submodule first). No submodules, or all clean: skip silently.
7a. **Peer check:** call `read_messages` first, every commit, whether or not `list_peers` shows anyone (it has returned a false empty list before, and a closed peer can still have left a message). If an unread message addresses this session, names a file in the pathspec or the feature being committed, or says stop / hold / don't commit or ship, act on it first: proceed only if it is clearly unrelated or superseded, otherwise narrow the pathspec or stop and ask. Then call `list_peers`; if another session is active in this repo, do NOT broadcast the pathspec: the Conductor daemon serialises commits in a project, and a pathspec commit never reads the index, so a peer's staged files cannot ride into this commit. Caveat: `commit-pathspec.sh` runs `git add` on untracked entries as a separate call before the commit, so a peer can interleave there. Call `post_message` only when a peer is mid-edit on a file in the pathspec (its messages or `list_peers` activity name it), addressed to that one peer, naming the file; then proceed, even inside a dedicated worktree (collisions happen at merge time). The same `read_messages` check runs again right before `git push` and before any deploy-style step after a commit (an upload to live, a publish). All three are MCP tools; if one is unavailable, skip it silently.
8. **Commit by pathspec, never stage-then-commit, via the script.** One call per commit, absolute path:

   ```
   bash ~/.claude/skills/commit/commit-pathspec.sh --expect-branch <1a EXPECTED branch> --expect-sha <1a EXPECTED sha> -m "<message>" -- <files>
   ```

   It runs, in order: prefilter gate, branch guard, HEAD guard, overlap-check, foreign-hunk-check, staged-pathspec coverage check, test-coverage check, the commit, then `git rev-parse HEAD` on its last line. Name every path (never `git add -A`, never `git commit -a`); the pathspec commit takes exactly those paths' working-tree state and never reads the index, so a peer's staged work cannot ride in, and no shared-index check is needed. Flags: `--own <comma-joined full shas>` = the OWN-COMMIT list (omit while empty), `--own-since <sha>` (merges `<sha>..HEAD` into `--own`), `--own-range <file>:<a>-<b>[,..]` per file (`bash ~/.claude/skills/commit/hunk-ranges.sh <files>` prints a file's current hunks as ready `--own-range` arguments plus each hunk's first changed line: keep only hunks this session wrote, never pass the whole line on trust), repeated `-m` (subject plus body paragraphs, never last-one-wins), repeatable `--todo <id>` (appends that todo's archive-move paths: `.claude/todos/done/<id>-*.md`, plus `.claude/todos/<id>-*.md` when git still tracks it; see `skills/close/ai-todos-format.md`).

   It ADVISES, never decides: every judgement branch refuses by default and needs `--force <check>`, one of `head-guard`, `overlap` (also `overlap-check`), `foreign-hunk`, `coverage`, `coverage-tests`, comma-joined or repeated. The branch guard and the prefilter gate take no override. The branch guard exists because a pathspec commit protects the INDEX from a peer's staged files but says nothing about which BRANCH receives the commit; on a mismatch, or detached `HEAD`, STOP and surface both branch names. On a HEAD-guard mismatch (a commit landed here since the run started, a peer detected from git alone) pick before committing: `post_message` on the repo channel and proceed, narrow the pathspec to avoid files the new commit touched, or stop and ask.

   **Foreign hunks.** The script derives `--own` ranges from `git diff HEAD`, trusted only when `hooks/.session-markers/` shows this session alone (one live marker or zero). With 2+ live markers it refuses with an explicit UNVERIFIED verdict unless a real `--own-range` is declared or `--force foreign-hunk` is given. A caller-declared `--own-range`, and a brand-new untracked file's derived range, stay trusted regardless. `--force foreign-hunk` on an UNVERIFIED file is not a bare override: a file with 2+ auto-derived hunks and no `--own-range` is REFUSED even with it (declare a per-hunk claim); a file with exactly one auto-derived hunk proceeds but first prints that hunk's `@@` header and first changed line under `hunk(s) taken on trust:`. Exit 1 `foreign-hunks-present <range>` = a separate hunk: drop that path or announce on the repo channel that you take the file whole, naming whose lines ride along. `foreign-hunks-inside-your-hunk <range>` = a peer's lines in the SAME `@@` hunk, which `git apply --cached` cannot split: the two safe orders are in `edge-cases.md` "Foreign hunk inside your own hunk". Never assume a dirty file in your pathspec is dirty only because of you. A path already deleted (`git rm` or plain delete) is excluded from the two checks that cannot diff it but kept in the commit.

   **Staged-pathspec coverage.** A `git mv` (or `complete-todo.ps1` archiving into `done/`) stages TWO paths; naming only the destination commits the copy and leaves the source deletion staged and unreported. A staged path outside the pathspec that shares a directory with one inside it: STOP, widen the pathspec or state why it stays. One in an unrelated directory is a peer's legitimate staged work: warn and name it, never block. Recovery for an already-landed half move: fold the omitted path in via `snippets/auto-commit.md` "Self-discovered: a file belongs in the commit you just made" (Case A `update-ref`), never `git commit --amend`.

   **Overlap policy** (the script's `overlap-check.sh` exit 1 = a real hunk-level hit against a commit this run did NOT make, printed `<file>:<range> <sha> <subject>`; `--own` shas print as info only, never exit 1; exit 2 = could not run, fix and rerun; with a pathspec above roughly a dozen files give the call an explicit `timeout` up to 600000ms). **On exit 1, evaluate in this order** (the commit-style ruling-out check runs before anything else):
   1. **Cross-ticket sharing forbidden:** if `.claude/commit-style.md` forbids sharing a commit across tickets and the blamed commit belongs to a different ticket, no fold is possible: skip `AskUserQuestion`, take the genuinely-separate branch, print one line naming the commit, the blamed lines and the quoted rule.
   2. **Personal repo - never ask:** `python ~/.claude/hooks/_client_repo.py is-client <repo>` reports `personal` (not in `refs/client-repos.txt`, including a repo with no remote): take the genuinely-separate branch, print one line naming the commit and blamed lines, skip the rest. Standing dev instruction, 2026-09-05: "we never have to fold, we can always just commit". The script proceeds on its own with an info line on a personal repo; a client repo (or `_client_repo.py` failing to run) refuses and names `--force overlap`. `/commit fold <sha>` typed by the dev is unaffected.
   3. **Client repo, interactive - queue, ask once at end-of-queue:** append commit, file and blamed lines to the overlap queue, take the separate branch, continue. When no further commit is pending and the queue is non-empty (and branch 4 does not apply), ask ONE `AskUserQuestion` naming every queued commit and its lines, offering `/commit fold <sha>` per item or proceed-as-is for all, never one question per commit; record the answer as the session's fold-policy.
   4. **A recorded fold-policy covers every queued item - reuse, don't re-ask:** applies at the same end-of-queue moment when the session holds a fold-policy AND every queued item is covered (none blamed on the literal current HEAD, none naming a commit from the session's cumulative own-commit list that the policy did not already see). Apply it without asking and say in the commit report which commits it covered and that it is a session-scoped reuse. A blamed commit that IS the current HEAD, or that this session made, always gets a fresh ask.
   5. **Unattended (`/auto-do-todos`, `/autopilot`, any caller that cannot block):** never ask; take the separate branch and record commit, file and blamed lines in the run's summary for after-the-fact review. This is the only place that behavior is defined.

   **Rules around the call.** (a) Never pipe the script (`| tail`, `| head`, `| grep`) and never chain `git push` after it (`&&`): either can swallow its non-zero exit and ship a refused commit. Run it unpiped (or `set -o pipefail`) and confirm success from its exit code or the `[commit] committed` line. (b) No AI attribution trailer: it refuses any `Co-Authored-By` or "Generated with" line in `-m`, even when the harness's attribution reminder asks for one; leave it out of the first attempt. (c) A message that is multiline or contains a literal `"`: in PowerShell a `-m` value with an embedded `"` passed to a native command word-splits (inline `@'...'@` or via a variable alike); escape every `"` as `\"`, and git unescapes it. (d) Untracked files: do not pre-`git add` them; the script stages a new file itself after its checks, and staging it first forfeits the exemption its untracked classification carries. (e) Never `git reset` or unstage entries you did not stage; the one exception is `/commit fold <sha>`'s own surfaced `reset --soft` on a dev-named sha. (f) Immediately after a successful commit run `git rev-parse HEAD` as its own call and append it to this run's OWN-COMMIT list and the session's cumulative list; report the `--short` form, never a sha read from the commit output (filters truncate it) or from memory. (g) After a multi-commit sweep, `git merge-base --is-ancestor <last-sha> <expected-branch>` confirms nothing landed off-branch. (h) Mass deletion or move of tracked files: pass the containing tree (`-- <tree-path>`), never a bare repo-wide pathspec (it would also sweep in unrelated uncommitted edits elsewhere). A pathspec picks up only already-tracked files, never untracked ones, so it stays within "know what you're committing" while `-A` does not. Sanity-check `git status` after and split off any unrelated edits.

   **Client-repo commit window:** in a client repo (`refs/client-repos.txt`), `hooks/commit-window-guard.py` denies every commit and push, `commit-pathspec.sh` and builders' raw `git commit` included, from 23:00 to 10:59 local unless Joe approved it this session. Follow its message (ask Joe, or defer to an 11:00 wake-up); never route around it and never shift a timestamp out of the window.

   **Shared-checkout hook hazard:** if the repo has a pre-commit hook (`git config core.hooksPath`) and is a shared `.git` checkout (`git rev-parse --git-common-dir` differs from `--git-dir`, or `.git/index.lock` exists), commit by hand per `by-hand.md` with `--no-verify` added (`commit-pathspec.sh` takes no such flag) and run the project's formatter/linter by hand first (a hook that stages, stashes or hides files is a working-tree risk pathspec commits do not cover). Full reasoning and recovery: `edge-cases.md`.

   **Script unavailable, or you need the reasoning behind a check:** `by-hand.md` has the whole chain done manually (preconditions, `git commit -m "<message>" -- <files>`, per-check meaning).
8b. **Post-commit index refresh, only if the repo runs `lint-staged` on pre-commit** (check `git config core.hooksPath` and read the `pre-commit` file for a `lint-staged` call). That hook rewrites the committed files in place, leaving their index entries stat-dirty though `git diff HEAD` is empty. Fix: `git add` the exact paths just committed and print which. Never `git reset` here (a shared checkout may have another session's work staged) and never `git update-index --refresh` (it only reports).

If nothing to commit, say so and stop.

## `/commit v` / `/commit bump`

Same as `/commit` but also bumps the patch version before committing (e.g. 1.0.0 -> 1.0.1).

1. Run `python C:/Users/tecno/.claude/skills/release/release.py bump <repo>`. It prints `{"version","build","label","files"}` and edits the version files itself (`edge-cases.md` has the Cargo scope rules).
2. Include every path in the printed `files` in step 8's commit pathspec.

Commit message follows the normal style - no mention of the bump. `bump` exits 2 with an `error`. When it starts "no version source", report it and commit normally without a bump. Any other error (a version file already dirty, a non-version line changed) means the bump was refused and its files restored: report it and stop, since committing first and then running `/commit onlyv` is usually the fix.

## Push pipeline

Moved to `skills/commit/push.md`; read it for any push (`/commit push`, a plain push request, `/release`). It holds the ordered pipeline (the ONLY place the whole sequence is enumerated) and these procedures, each under its own heading there: **Gate hand-off**, **Pre-push todo sweep**, **Pre-push transcript check**, **Pre-push gate**, **Post-push ticket move**, the `/commit push` mode (pending-bump note, push rule), and the client-repo commit-window rule (`hooks/commit-window-guard.py` denies commits and pushes 23:00-10:59 local in a client repo unless Joe approved it this session). Adding, removing or reordering a push step means editing that list in the same commit. A plain push never bumps a version: that is `/release`.

## `/commit push`

Same as `/commit` but also runs `git push` after committing, following `push.md` in order (never push when the commit failed; zero ahead means "nothing to commit, nothing to push").

## `/commit onlyv` / `/commit onlybump`

Only bumps the patch version. No other changes staged. Commit message is always `CHORE: bump to v1.0.1` (the actual new version). Procedure: same as `/commit v`; when `bump` exits 2 (no version source), report its error and stop.

## `/commit fold <sha>`

Folds fixes into an existing UNPUSHED commit `<sha>` the dev names, preserving every other commit's message, author and timestamp. Read `skills/commit/fold.md` first and follow it in full: its preconditions (the pushed check must query the live remote, never local refs) run before anything is written. If `<sha>` is HEAD and nothing landed on top, `snippets/auto-commit.md` Case A is simpler; use that instead.

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
- **Target repo other than cwd:** if the dev or a prior instruction names a repo path other than the current project, use `git -C <path>` for every git command this run issues, not just some, and state that repo path in the first line of output.
- Name every path in the commit pathspec (step 8). Never `git add -A`, never `git commit -a`. Exception for mass deletion/move: step 8 rule (h).

## Edge cases and grouping

Rare paths, read on demand: `skills/commit/edge-cases.md` covers merge-commit resolution, splitting one file's changes across commits (`python skills/commit/split-hunks.py stage|commit`: `stage` for solo partial staging, `commit` for a shared-index-safe partial commit), backdating, branch protection and submodules.

**Shared-component swaps:** when a file's only change is swapping a local implementation for a shared / design-system component, it belongs with the commit that adds or changes that shared component, not the feature commit that triggered the swap. If the file also carries feature-specific edits, split it via partial staging (`edge-cases.md`): swap hunks with the component commit, the rest with the feature.
