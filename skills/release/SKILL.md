---
name: release
description: "Triggers on /release or 'make a new version': push pipeline plus kit sync and version bump. Not for a plain push."
# Every step is a script call or a fixed procedure, so the session's top-tier model buys nothing here.
model: sonnet
effort: medium
---

# /release

> Push pipeline plus three extra steps: 1b kit sync, 4a pre-bump checks and 4b version bump. A plain push ("push it", `/commit push`) never bumps a version.

The sequence is `skills/commit/SKILL.md`'s "Push pipeline" list, the only place it is enumerated. This skill adds the mode decision and the release-only steps (1b, 1d, 4a, 4b), all defined below. "Unattended" means the same as in `/commit`: `/autopilot`, `/auto-do-todos`, `/mega-todos`, or any caller that cannot block on a question.

## Mode

1. `python C:/Users/tecno/.claude/skills/release/ship-config.py get <repo>` prints `{"class","todo_sweep","release","slug","source","reason"}`.
2. Class `unknown` (attended or not): show the resolver's `reason` and stop without pushing. Never ask the card: `ship-config.py set` always refuses class `unknown`. Class `client` with `release: null` (no override yet):
   - Unattended: stop without pushing, "no release mode for <slug>; run /release attended once".
   - Attended: one `ask_user_question` card, options "No bump, push only" / "Patch bump + VERSION commit". Then `ship-config.py set <repo> release=none|patch`, which prints `{"path"}` (exit 2: show its message, stop). Commit that file by pathspec in its own repo: personal, the project repo; client, the ~/.claude repo via `git -C C:/Users/tecno/.claude` (never pushed). Continue.
3. `release: "none"`: say "/release here is a plain push (release: none)" and run the Push pipeline without 1b, 4a and 4b.
4. `release: "patch"`: run the Push pipeline with 1b, 4a and 4b.
5. After 1b: when the branch has no upstream (`git rev-list --count @{u}..HEAD` errors), say so and offer `git push -u origin <branch>`, same as `/commit`'s push rule; the count check below applies once an upstream exists. When `git rev-list --count @{u}..HEAD` is 0 and `release.py version-diff <repo>` shows nothing pending, print "nothing to release" and stop. A release is never version-only.

## Gate chat

An attended `/release` from a chat that has used 30% or more of its context, or that is in Subchats mode (the gate then runs as a hidden gate sub, see `/gate-chat` step 2), hands the rest of the pipeline (from the todo sweep on, including 4b) to a fresh gate chat that ends with `/close`: after 1b, 1d and the Mode step 5 check, invoke `/gate-chat` with mode `release` and the resolved `release` value. If `/gate-chat` finds the chat under 30% with Subchats mode off it returns and the pipeline continues here; otherwise this chat stops. Unattended runs keep the gate in place.

## 1b. Kit sync

`python C:/Users/tecno/.claude/skills/release/release.py kit-sync <repo>` prints `{"changed","old","new"}`. When `changed`, commit `CHORE: bump tauri_kit <old> -> <new>` (ASCII arrow) via `commit-pathspec.sh` with pathspec `vendor/tauri_kit`. It runs before the todo sweep and the gate so `/code-check` and `/e2e` cover the new kit code.

## 1d. Repo reports

Runs after 1b, before the Gate chat hand-off, so Joe reads it in this chat. When the repo has `.claude/release-reports.txt`, run each non-blank line that does not start with `#` as a shell command from the repo root (PowerShell on Windows) and show its output to Joe under the command as a heading. The file is the repo's own list of "look at this before it ships" reports, for example a log of failures the app recorded but never showed. No file: skip silently.

- Advisory only: a non-zero exit or an alarming table never stops the release. Say what stood out in one sentence; when something looks like a real defect, offer to file a todo for it through the `ask_user_question` card.
- Unattended: run the commands, put the output in the run's report, never ask.

## 4a. Pre-bump checks

Runs after the gate is green, before 4b, so a build the repo's own check rejects never gets a VERSION commit (a CI-only smoke failure once cost a version number, todo 1319).

`python C:/Users/tecno/.claude/skills/release/release.py pre-bump <repo>` runs each non-blank line of the repo's `.claude/pre-bump.txt` that does not start with `#` as a shell command from the repo root, in order, and prints `{"ran": [...]}`. No file: it runs nothing, skip silently. Output of the commands goes to stderr; allow the call an explicit `timeout` of 600000ms or run it in the background, since a smoke check can build an image (the script itself allows each command 30 minutes).

- Exit 0: continue to 4b.
- Exit 1: a command failed or timed out. Stop without bumping or pushing, show the `error` line and the command's output, and fix or ask. Attended: ask through `ask_user_question` whether to release anyway, naming the failing command; yes means continue to 4b and put "pre-bump check failed, approved by Joe" in the `mark --reason`. Unattended: stop and report, never override.
- The file is the repo declaring "this must pass before a version ships", so a failure blocks, unlike 1d's advisory reports. The repo owns the commands; this skill names none. It runs only when 4b does (`release: patch`).

## 4b. Version bump

Runs after the gate is green, before `push-gate.py mark`.

1. `release.py version-diff <repo>`. `pending: true`: skip the bump and say "skipped: unpushed bump <base_version> -> <head_version> already in range". Exit 3 (fetch failed): unattended, stop without pushing; attended, ask. Exit 2 (no base ref, or unrelated history): stop, report its error, do not push.
2. Otherwise `release.py bump <repo>` prints `{"version","build","label","files"}`. Commit exactly those `files` via `commit-pathspec.sh` as `VERSION: <label>`. Exit 2 (no version source, including an explicit `release: patch` on a repo without one): stop, report its error, do not push, never fall back to a plain push.
3. `push-gate.py mark --reason` names "version bump after gate".

The bump sits after the gate so todo-sweep folds and `/code-check` fix folds never land in the VERSION commit and a red gate never leaves a bump behind.
