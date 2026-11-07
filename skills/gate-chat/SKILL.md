---
name: gate-chat
description: Hands a push's gate (code-check, e2e, push) to a fresh chat ending in /close. Called by /commit and /release.
---

# /gate-chat

> The gate is the heaviest part of a push. A fresh chat runs it on an empty context, with its one job being to ship and then close. Called from `/commit`'s Push pipeline step 1c, for an attended push or `/release` from a chat that has used 30% or more of its context.

Runs after step 1 (and 1b and 1d under `/release`), once `git rev-list --count '@{u}..HEAD'` says there is something to push. If `@{u}` does not resolve (a branch with no upstream), say so, offer `git push -u origin <branch>` instead, and stop: there is no range to hand over. It does not apply to:

- **A chat under 30% context used**: run `node ~/.claude/skills/context-left/context-left.mjs`, which prints `context left: <n> / <window> (<pct>%)`. 70% or more left means stop here and return: the pipeline continues in this chat. Joe set this threshold on 2026-10-27 ("only when context is heavy, over 30% used"); a 2026-10-29 "Gate chat, always" answer was about `/release` as a runner, not a new threshold.
- **Unattended runs** (`/autopilot`, `/auto-do-todos`, `/mega-todos`): nobody would answer the gate chat's cards, so the gate stays in place.
- **A chat that is itself a gate chat** (its first message quotes a hand-off): it already holds the fresh context, so it skips step 1c and runs the gate where it stands. Without this a gate chat would spawn another forever.

## Procedure

1. Run the **Pre-push transcript check** (`skills/commit/SKILL.md`) now. It reads THIS session's transcript, which a gate chat cannot see, so it never moves. An unaddressed dev turn stops the push here, before any spawn.
2. `spawn_chat` with `cwd` = the repo root, `name` = `Gate: <repo> <push|release>`, `model` = `sonnet` and `effort` = `high` (Joe's standing choice for every push and release gate; omitting them makes the child inherit the parent's model, which put a gate on Fable). High, not medium: the gate's code-check judges the final pushed range, and a miss there ships. The prompt carries everything, since the new chat cannot see this one:
   - Joe's push request, quoted verbatim, and the mode (`push`, or `/release` with its resolved `release` mode).
   - Repo path, branch, `git rev-parse HEAD` and `git log --format='%h %s' '@{u}..HEAD'` (the no-upstream case already stopped above, so `@{u}` resolves).
   - "The transcript check ran in the parent chat and passed; skip step 3." Plus any in-session client commit-window OK Joe gave here, quoted.
   - The instruction: run `/commit`'s Push pipeline from step 2 (4b only under `/release`: tell the child to read `skills/release/SKILL.md` section 4b, which has the `release.py bump` exit-code handling and the `--reason "version bump after gate"` mark; it does not load `/release` itself), skipping step 1c. On a red gate or any question, ask Joe in that chat.
   - "Read `snippets/auto-commit.md` before the push." `hooks/push-read-gate.py` denies a session's first `git push` until the file was read in that session, and a fresh gate chat has read nothing, so the pre-read costs one call instead of a denied push and a retry.
   - The literal token `/close` as the prompt's last word. `/close` finishes the open work first, keeps the chat open on an unanswered question, and closes it only once the work is pushed, so a red gate never closes behind Joe's back. Because the token ends the prompt rather than starting it, Conductor does not mark the chat Closing while the gate runs.
3. Tell Joe the gate moved to the new chat, and stop: this chat does not push, and makes no further commits in that repo until the gate chat reports pushed (its HEAD guard would refuse anyway).

A gate chat spawned this way carries the parent's push ask, per `snippets/auto-commit.md`.
