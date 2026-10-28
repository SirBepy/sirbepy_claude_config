<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Add a deploy button to Claude Conductor

**Type:** task
**Origin:** dev

## Goal

Give Joe a button in `claude_usage_in_taskbar` (Claude Conductor) that deploys the current
project, so deploying is one click and not one typed command. Settled 2026-08-29: the button is a
second surface onto the existing `/deploy` skill, never a second implementation.

## Context

`/deploy` shipped 2026-08-29 (`~/.claude/skills/deploy/SKILL.md`). It fires the current repo's own
`.github/workflows/deploy.yml` via `workflow_dispatch`, watches the run with
`gh run watch --exit-status`, and holds no per-project knowledge - each repo owns its deploy.yml.

Joe's requirement, in his words: "i wanna be able to use the same skill/command/button to deploy
any project". The CI substrate is what makes that possible, because `gh workflow run deploy.yml`
is identical in every repo and needs no local credentials.

**The button must not reimplement any of this.** Conductor already has a send-to-session path -
`src-tauri/src/ipc/chat/run.rs:134` (`send_message`), with a client method at
`src-tauri/src/daemon_client/methods/sessions.rs:59`. The button injects `/deploy` into the active
session and lets the skill do the work. That keeps one implementation behind two surfaces.

Verified 2026-08-29 by reading those files; the exact UI wiring (where the button lives, how it
learns whether the current repo is deployable) was NOT investigated and is the open part.

## Approach

1. Find how existing buttons/actions are declared in the frontend SPA (`src/views/sessions/`) and
   what they call.
2. Add a deploy button, enabled only when the session's repo has a `deploy.yml` on its default
   branch - reuse the same check `/deploy`'s preflight does rather than inventing a second one.
3. On click, `send_message` with `/deploy` into that session.
4. Disabled/hidden state for a repo with no deploy.yml, so the button never silently no-ops.

Rejected: having the button shell out to `gh` from Rust. That would duplicate the preflight,
confirmation and watch logic, and the two surfaces would drift.

## Acceptance

- Button appears for a repo with a `deploy.yml` and is absent/disabled for one without.
- Clicking it produces a normal `/deploy` run in the session, indistinguishable from typing it.
- No deploy logic lives in the Rust or frontend code - only the injection.
- `pnpm vitest run --poolOptions.threads.maxThreads=5 --poolOptions.threads.minThreads=1` passes
  (per that repo's CLAUDE.md; never `--pool=forks --singleFork`, it produces ~15 false failures).

## Notes

- This is a Tauri app: `cargo build --manifest-path src-tauri/Cargo.toml` is the verify step, and
  it is slow. Budget for it.
- Deferred from the 2026-08-29 session that built `/deploy` because the Rust build was more than
  that session had left; Joe chose "skill + Hubbub workflow" as that session's scope.
- Relocated to 910 in claude_usage_in_taskbar (remote: SirBepy/claude_conductor) via /mega-todos 2026-09-04, on Joe's explicit say-so. It was misfiled here: every file it targets lives in that repo, which has its own active backlog. Placement of the button is that session's call.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [UX] This todo is MISFILED: every file it targets lives in `claude_usage_in_taskbar`, which has its own active backlog. It is dev-origin, so relocating it needs your say-so. Separately, where should the deploy button live? Options: relocate to `claude_usage_in_taskbar`'s backlog and answer placement there / relocate and let that session decide placement / leave it filed here. Recommended: relocate. On placement, a toolbar icon beside the existing session actions matches the pattern already in that app.
