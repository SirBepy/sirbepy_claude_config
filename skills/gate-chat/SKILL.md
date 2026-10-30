---
name: gate-chat
description: Hands a push's gate (code-check, e2e, push) to a fresh chat ending in /close. Called by /commit and /release.
---

# /gate-chat

> The gate is the heaviest part of a push. A fresh chat runs it on an empty context, with its one job being to ship and then close. Called from `/commit`'s Push pipeline step 1c, for every attended push and every `/release`.

Runs after step 1 (and 1b under `/release`), once `git rev-list --count '@{u}..HEAD'` says there is something to push. It does not apply to:

- **Unattended runs** (`/autopilot`, `/auto-do-todos`, `/mega-todos`): nobody would answer the gate chat's cards, so the gate stays in place.
- **A chat that is itself a gate chat** (its first message quotes a hand-off): it already holds the fresh context, so it skips step 1c and runs the gate where it stands. Without this a gate chat would spawn another forever.

## Procedure

1. Run the **Pre-push transcript check** (`skills/commit/SKILL.md`) now. It reads THIS session's transcript, which a gate chat cannot see, so it never moves. An unaddressed dev turn stops the push here, before any spawn.
2. `spawn_chat` with `cwd` = the repo root and `name` = `Gate: <repo> <push|release>`. The prompt carries everything, since the new chat cannot see this one:
   - Joe's push request, quoted verbatim, and the mode (`push`, or `/release` with its resolved `release` mode).
   - Repo path, branch, `git rev-parse HEAD` and `git log --format='%h %s' '@{u}..HEAD'`.
   - "The transcript check ran in the parent chat and passed; skip step 3." Plus any in-session client commit-window OK Joe gave here, quoted.
   - The instruction: run `/commit`'s Push pipeline from step 2 (4b only under `/release`), skipping step 1c. On a red gate or any question, ask Joe in that chat.
   - The literal token `/close` as the prompt's last word. `/close` finishes the open work first, keeps the chat open on an unanswered question, and closes it only once the work is pushed, so a red gate never closes behind Joe's back. Because the token ends the prompt rather than starting it, Conductor does not mark the chat Closing while the gate runs.
3. Tell Joe the gate moved to the new chat, and stop: this chat does not push, and makes no further commits in that repo until the gate chat reports pushed (its HEAD guard would refuse anyway).

A gate chat spawned this way carries the parent's push ask, per `snippets/auto-commit.md`.
