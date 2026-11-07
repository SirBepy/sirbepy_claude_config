# /commit push: pipeline and pre/post-push procedures

Read on demand from `skills/commit/SKILL.md` (the `## Push pipeline` pointer). Everything the push path needs lives here: the ordered pipeline, the gate hand-off, the todo sweep, the transcript check, the gate, the post-push ticket move and the `/commit push` mode itself. Other skills cite these section names (`Pre-push gate`, `Pre-push transcript check`, `Gate hand-off`, `Pre-push todo sweep`, `Post-push ticket move`); they resolve here.

## Push pipeline

The full ordered sequence for every push (`/commit push`, a plain push request, and `/release`); steps marked `/release only` are skipped otherwise. This list is the ONLY place the whole sequence is enumerated: `CLAUDE.md`, snippets and memories point here instead of restating it, because every restated copy has drifted the moment a step was added (the todo sweep reached this file while two summaries still listed only `/code-check` + `/e2e`). Adding, removing or reordering a push step means editing this list in the same commit. When describing what a push will run, read this list, never a summary of it.

1. **Commit** - steps 1-8 of `SKILL.md`, including step 6b's gate (`/test` plus the test-coverage check).
1b. **Kit sync** (`/release only`) - `release.py kit-sync <repo>`, then a `CHORE: bump tauri_kit <old> -> <new>` commit when the submodule pointer moved. Before the sweep and gate so `/code-check` and `/e2e` cover the new kit code.
1d. **Repo reports** (`/release only`) - advisory output a repo asks to see before it ships: each command line of its `.claude/release-reports.txt`, run from the repo root, output shown to Joe. Never blocks. Runs in this chat, before any gate hand-off, because the gate chat closes itself and Joe reads this one.
1c. **Gate hand-off** - attended runs only, when this chat has used 30% or more of its context, or is in Subchats mode (the gate then runs as a hidden gate sub, whatever the context level): run step 3 here, then hand steps 2 and 4 onward to a fresh gate chat that ends with `/close` (see "Gate hand-off" below). The gate is the heaviest part of a push, and a long chat runs it on a crowded context. Under 30% used, the gate runs in place: a spawned chat costs a cold start and buys nothing on a light context (Joe, 2026-10-27, and again 2026-10-30 after a 13%-context chat spawned one anyway).
2. **Pre-push todo sweep** - fold small backlog todos sitting in the files the push already touches.
3. **Pre-push transcript check** - stop on any dev message since the last push that was never addressed.
4. **Pre-push gate** - `/code-check` over `@{u}..HEAD`, the unit tests CI runs, and `/e2e` (or its no-suite note), started together where they do not share a lock, then mark HEAD cleared.
4a. **Pre-bump checks** (`/release only`) - `release.py pre-bump`, the commands a repo lists in `.claude/pre-bump.txt`; a failure stops the release before step 4b.
4b. **Version bump** (`/release only`) - `release.py version-diff`, then `release.py bump` and a `VERSION: <label>` commit. After the gate so sweep folds and `/code-check` fix folds never land in the VERSION commit and a red gate never leaves a bump behind; the `mark` follows the bump.
5. **`git push`**.
6. **Post-push ticket move** - every ticket the push shipped goes to Testing.
7. **Build watch** - `skills/commit/build-watch.md`.

**Client-repo commit window.** In a client repo (`refs/client-repos.txt`), `hooks/commit-window-guard.py` denies every commit and push (step 8 and step 5 alike, including `commit-pathspec.sh` and `/mega-todos` builders' raw `git commit`) from 23:00 to 10:59 local, unless Joe approved it in this session. On a denial, follow its message: ask Joe, or defer to an 11:00 wake-up. Never route around it, and never shift a timestamp out of the window.

## Gate hand-off

Runs after step 1 (and 1b under `/release`), for an attended push or `/release` from a chat that has used 30% or more of its context or is in Subchats mode. Invoke `/gate-chat` through the Skill tool and follow it in full: it measures the context, then runs the transcript check here, spawns the gate chat with `/close` at the end of its prompt, and stops this chat. Under 30% with Subchats mode off it returns and the pipeline continues here. Unattended runs (`/autopilot`, `/auto-do-todos`, `/mega-todos`) and a chat that is itself a gate chat skip it and keep the gate in place.

## Pre-push todo sweep

Runs for every push (`/commit push`, a plain push request, and `/release`), as Push pipeline step 2: in the gate chat when step 1c handed off, otherwise in place, and always before the gate below - it can change what the push ships, so the gate must see the final range. Catches a small backlog todo sitting in the exact files the push already touches, while folding it in is still free.

1. Skip silently when `python C:/Users/tecno/.claude/skills/release/ship-config.py get <repo>` reports `todo_sweep: false` (personal repos default to off, client and unknown repos to on), or when the repo has no `.claude/todos/` backlog with open todos. Skip on an unattended run too (nobody to answer step 3), with one line in the run's report saying the sweep was skipped.
2. Dispatch ONE read-only subagent (`model: 'sonnet'`, canonical preamble from `refs/builder-preamble.md` with the `READ-ONLY DISPATCH` opt-out). Hand it the backlog path and `git log --format='%H %s' --name-only '@{u}..HEAD'`. A todo qualifies only when all three hold: it touches files an unpushed commit already changes, it is EASY by `/batch-todos`'s table, and it is the same concern or ticket as that commit. Todos with a live claim in `.claims/` and PRODUCT todos never qualify. It returns per hit: todo id, target commit sha, files, and one line on why it fits; zero hits is a valid answer, never padded.
3. Zero hits: proceed silently. Otherwise one `ask_user_question` card, `multiSelect`, one option per hit (todo id, target commit subject, why it fits) plus "none, push as is".
4. Per approved todo: claim it per `skills/close/ai-todos-format.md`, implement it, rerun the fast checks, then fold it into its target commit - Case A in `snippets/auto-commit.md` when the target is HEAD, `/commit fold <sha>` otherwise. When the fold path refuses (overlap with a later commit), commit it on top as its own commit instead, never force the fold. Close the todo and release the claim per the contract.

## Pre-push transcript check

Runs for every push (`/commit push`, a plain push request, and `/release`), as Push pipeline step 3 - never for a plain `/commit` or version-only bump, which stay untaxed. It reads THIS chat's transcript, so on an attended push handed to a gate chat (step 1c) it runs here in the parent chat before the spawn, and the gate chat skips it; otherwise it runs in place after the sweep and before the gate. Catches a dev instruction that landed in the transcript but never reached the working context, before the push ships whatever got built on the gap (todo 902: a rejected layout was built, committed, and pushed because a peer relay sat between the dev's correction and the next turn).

1. Resolve the transcript path via `skills/close/grounding.md` (the "Transcript grounding" recipe in `skills/close/SKILL.md`) (`~/.claude/sessions/*.json` for `sessionId`, then the sanitised-cwd `.jsonl`) - do not re-derive it. `Grep`, never `Read`: transcripts embed full tool payloads and run to megabytes.
2. Reference point: this session's own last successful push, recalled from an earlier push report in this conversation, never re-derived from git. No prior push this session: the transcript's first line.
3. Grep `"type":"user"` lines after that point whose content is text, not a `tool_result`. A `[daemon-meta]` peer relay is not itself a dev turn, but leave it in the scanned range - it is exactly what can sit between two dev turns and bury one, per the incident above.
4. For each dev text turn found, confirm it was addressed: referenced or acted on later in this conversation, or explicitly superseded by a later dev message. A correction, rejection, or preference ("i dont like...", "no, instead...", "wait, actually...") with no visible acknowledgement afterward is unaddressed.
5. No dev turns since the reference point, or all addressed: proceed silently, no added output.
6. Any unaddressed turn: stop before `git push`, quote the message verbatim, and ask whether to address it now or push anyway.

## Pre-push gate

Runs as Push pipeline step 4, after the sweep and the transcript check (in the gate chat when step 1c handed off, otherwise in place), for every push, in every repo. `hooks/push-gate.py` blocks the push until this gate clears HEAD, so skipping it only earns a denied `git push`.

**Start the independent steps together.** Steps 1, 1a and the build `/e2e` needs (step 2) do not depend on each other: dispatch step 1's code-check subagent in the background first (the Agent tool backgrounds by default), then run 1a and the e2e build while it works, and join on all of them before step 3. A red result from any still blocks `mark`. Only serialize what shares a lock: two cargo commands in one repo share the target dir, so 1a and the e2e build run one after the other, never concurrently. A code-check fix that edits files re-runs 1a and the build for the files it touched.

1. `/code-check` over what this push ships (`@{u}..HEAD`). Fix findings about lines the push changes, recommit per the fold rules, rerun; findings about untouched code go to the backlog. When the range is a long unpushed stack (a `/loop-todos` or `/autopilot` run, roughly 10+ commits), also run `skills/review-unpushed/SKILL.md`'s per-commit correctness review first: `/code-check` reviews structure, not each commit's logic.
1a. **Unit tests CI runs.** Run the same unit-test commands the repo's CI `test` job runs, over the working tree at HEAD, unpiped (cargo-test-pipe-guard) and with an explicit timeout up to 600000 or in the background. Find them in the `test` job of `.github/workflows/*.yml`; a repo with no CI test job or no GitHub remote skips this step with one line saying so. `/test` at commit time is not a substitute: it covers what the commit touched, this covers the whole range, and a peer's half-finished work can leave a suite red between commits (2026-11-06, claude_usage_in_taskbar: `cargo test --lib` was red in CI on `mcp::dispatch::tests::send_message_forwards_every_validated_schema_property` because `visuals` was never relayed; the local gate had no such step, so it cost a second CI round). Skip a command the job itself marks as slow or integration-only and name it in the mark reason; a red test is a red gate, fixed by a new commit per the fold rules and then re-run.
2. `/e2e` against the same range. **No suite** means `/e2e`'s Run-mode table matches only its "anything else" row (no scripted path). Then branch on `python C:/Users/tecno/.claude/hooks/_client_repo.py is-client <repo>`: `client` gets `/e2e`'s drive-it-by-hand fallback, per `snippets/client-repo.md`; `personal` skips e2e without asking and records "e2e: no suite" in the mark reason.
3. All green (under `/release`, step 4b runs first and its `--reason` names "version bump after gate"): `python C:/Users/tecno/.claude/hooks/push-gate.py mark <repo> --reason "<what passed, e.g. code-check + e2e passed, or code-check passed, e2e: no suite>"`, then push. **The `mark` call and `git push` must be separate tool calls, never chained with `&&`/`;`** - same reason the commit-guard marker at the top of `SKILL.md` must be its own call: the hook inspects the whole command string before any of it runs, so a chained `mark && git push` is denied because the mark has not been written yet when the hook checks for it. `mark` also reads this session's transcript and refuses unless `/test` and `/e2e` (plus `/flutter-e2e` in a Flutter repo) were loaded through the Skill tool since the last push; `e2e: no suite` in the reason waives the e2e half, a gate chat is not asked for `/test`, and when the dev approved pushing past a red check, add `--skip-skill-check "<his approval>"`.
4. Either one red or impossible to run: ask the dev through `ask_user_question` whether to push anyway, naming the failure. Yes: mark with `--reason` naming the failure and his approval, then push. No, or an unattended run with nobody to ask: do not push, report the failure.

## Post-push ticket move

Runs right after a successful `git push`, in every push mode, attended or not. QA works from the board, not the git log, so a pushed fix still sitting in In Progress never reaches the person who tests it next (2026-09-03: eight pushed tickets left in In Progress; 2026-10-05: sc-54701 pushed and left In Progress, then Claude asked Joe where to move it instead of moving it).

1. Collect ticket ids from the subjects of the commits the push shipped (record `@{u}..HEAD` before pushing): `<id>:` prefixes, `sc-<id>`, `[SC-<id>]`, or a Linear key. No ids: skip silently.
2. Infer the tracker from `origin` the way `/ticket` does. Move a ticket only when Joe owns it and it sits before Testing (Backlog, To Do, In Progress, Blocked, PR Review, On hold). Shortcut: GET the story, then PUT only `workflow_state_id` with the Testing state of the story's own workflow (ENG - Core Workflow: `500018257`). Never send `custom_fields`, because PUT replaces them. If the story's workflow has no Testing-equivalent state, skip it and say so. Linear: the team's Testing/review state, same rules.
3. Testing is the ceiling. Never move a ticket to Ready for deploy or Complete: QA promotes it from Testing, and the release skill closes it from there. A ticket already in Testing or later stays where it is, including one QA bounced and that was just re-fixed.
4. Change the state only. Post no comment and draft no QA note unless the dev asks for one.
5. Name the moved ids in the push report, plus each skipped id and why.

## `/commit push`

Same as `/commit` but also runs `git push` after committing, following the **Push pipeline** above in order (this file). A plain push never bumps a version: that is `/release`.

**Pending-bump note:** before pushing, run `python C:/Users/tecno/.claude/skills/release/release.py version-diff <repo> --no-fetch`. When it prints `pending: true`, add "range includes a pending version bump <base> -> <head>" to the push report, so a bump left behind by a failed `/release` never ships silently. A non-zero exit is non-blocking: omit the note.

**Push rule:** if the commit step failed, do not push. If there was nothing to commit, don't stop there either - check `git rev-list --count '@{u}..HEAD'` (if `@{u}` doesn't resolve, say so and offer `git push -u origin <branch>` instead of silently doing nothing). Zero ahead: say "nothing to commit, nothing to push" and stop. One or more ahead: follow the **Push pipeline** from step 1c, exactly like the commit path: on an attended run at 30% or more context used or in Subchats mode, `/gate-chat` runs the **Pre-push transcript check** here and hands the **Pre-push todo sweep** and **Pre-push gate** to a fresh chat; otherwise run all three in place in that order (sweep, transcript check, gate). Then push those existing commits and report how many.

After a successful push, run the **Post-push ticket move**, then the **Build watch** (see `skills/commit/build-watch.md`).
