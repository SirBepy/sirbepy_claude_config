---
name: release
description: "Triggers on /release or 'make a new version': push pipeline plus kit sync and version bump. Not for a plain push."
---

# /release

> Push pipeline plus two extra steps: 1b kit sync and 4b version bump. A plain push ("push it", `/commit push`) never bumps a version.

The sequence is `skills/commit/SKILL.md`'s "Push pipeline" list, the only place it is enumerated. This skill adds the mode decision and the two release-only steps, both defined below. "Unattended" means the same as in `/commit`: `/autopilot`, `/auto-do-todos`, `/mega-todos`, or any caller that cannot block on a question.

## Mode

1. `python C:/Users/tecno/.claude/skills/release/ship-config.py get <repo>` prints `{"class","todo_sweep","release","slug","source","reason"}`.
2. Class `unknown` (attended or not): show the resolver's `reason` and stop without pushing. Never ask the card: `ship-config.py set` always refuses class `unknown`. Class `client` with `release: null` (no override yet):
   - Unattended: stop without pushing, "no release mode for <slug>; run /release attended once".
   - Attended: one `ask_user_question` card, options "No bump, push only" / "Patch bump + VERSION commit". Then `ship-config.py set <repo> release=none|patch`, which prints `{"path"}` (exit 2: show its message, stop). Commit that file by pathspec in its own repo: personal, the project repo; client, the ~/.claude repo via `git -C C:/Users/tecno/.claude` (never pushed). Continue.
3. `release: "none"`: say "/release here is a plain push (release: none)" and run the Push pipeline without 1b and 4b.
4. `release: "patch"`: run the Push pipeline with 1b and 4b.
5. After 1b: when the branch has no upstream (`git rev-list --count @{u}..HEAD` errors), say so and offer `git push -u origin <branch>`, same as `/commit`'s push rule; the count check below applies once an upstream exists. When `git rev-list --count @{u}..HEAD` is 0 and `release.py version-diff <repo>` shows nothing pending, print "nothing to release" and stop. A release is never version-only.

## 1b. Kit sync

`python C:/Users/tecno/.claude/skills/release/release.py kit-sync <repo>` prints `{"changed","old","new"}`. When `changed`, commit `CHORE: bump tauri_kit <old> -> <new>` (ASCII arrow) via `commit-pathspec.sh` with pathspec `vendor/tauri_kit`. It runs before the todo sweep and the gate so `/code-check` and `/e2e` cover the new kit code.

## 4b. Version bump

Runs after the gate is green, before `push-gate.py mark`.

1. `release.py version-diff <repo>`. `pending: true`: skip the bump and say "skipped: unpushed bump <base_version> -> <head_version> already in range". Exit 3 (fetch failed): unattended, stop without pushing; attended, ask. Exit 2 (no base ref, or unrelated history): stop, report its error, do not push.
2. Otherwise `release.py bump <repo>` prints `{"version","build","label","files"}`. Commit exactly those `files` via `commit-pathspec.sh` as `VERSION: <label>`. Exit 2 (no version source, including an explicit `release: patch` on a repo without one): stop, report its error, do not push, never fall back to a plain push.
3. `push-gate.py mark --reason` names "version bump after gate".

The bump sits after the gate so todo-sweep folds and `/code-check` fix folds never land in the VERSION commit and a red gate never leaves a bump behind.
