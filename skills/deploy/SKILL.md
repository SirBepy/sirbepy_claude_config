---
name: deploy
description: Triggers on /deploy only. Fires the current repo's own deploy.yml via workflow_dispatch and watches the run. Holds no per-project deploy knowledge.
disable-model-invocation: true
argument-hint: "[--ref <branch>] [--no-watch]"
---

# /deploy

> One command, any project. The skill knows how to *trigger* a deploy; the repo knows what
> deploying means.

**Trigger:** `/deploy` only. Never auto-invoke - deploying is outward-facing.

## The contract

A repo is deployable when it has `.github/workflows/deploy.yml` with a `workflow_dispatch`
trigger. That file owns every project-specific detail: build steps, secrets, target, checkout
layout. This skill only fires it and reports back.

That split is the whole point. Adding a new deployable project means writing its `deploy.yml`,
never editing this skill.

**`workflow_dispatch` only registers if the workflow exists on the repo's DEFAULT branch.** A
`deploy.yml` sitting only on a feature branch is invisible to `gh workflow run`, which fails with
a bare "could not find any workflows named deploy.yml" - a message that reads like a typo rather
than a branch problem. Check the default branch, not the working tree, and say which one is
missing it.

## Steps

### 1. Preflight

Stop with a plain explanation if any fail. Never half-deploy.

- `gh --version` succeeds, and `gh repo view` resolves (the global `gh-account-switch.sh` hook
  has already matched the account to the remote by the time this runs).
- `deploy.yml` exists **on the default branch**:
  `gh api repos/{owner}/{repo}/contents/.github/workflows/deploy.yml?ref=<default> --silent`.
  If missing, say so and name what to add - do not scaffold one uninvited.
- Working tree clean. If dirty: run `/commit push` per the global rule (never a raw `git
  commit`), because CI deploys a pushed ref and uncommitted work would silently not ship.
- No unpushed commits. If any: push them, same reason.

### 2. Confirm

CI deploys a ref, so the ref is the whole decision. Show it and wait:

- repo slug, branch, short sha, and the sha's commit subject
- the workflow file about to run

Ask via `AskUserQuestion`: deploy / pick another ref / cancel. Skip this only when the invoking
prompt carries an explicit go-word (`/deploy go`, "just deploy it").

### 3. Dispatch

Capture a baseline BEFORE firing, so the run being watched is provably the new one:

```
gh run list --workflow deploy.yml --limit 1 --json databaseId -q '.[0].databaseId'
```

Then `gh workflow run deploy.yml --ref <branch>`.

`gh workflow run` prints nothing useful and **returns no run id** - the run takes a few seconds to
register. Poll `gh run list --workflow deploy.yml --limit 5 --json databaseId,createdAt` until an
id appears that is not the baseline, for up to ~60s. Never assume the newest row is yours: a
concurrent push, or a second person deploying, puts someone else's run at the top.

If no new run registers within 60s, say the dispatch did not take and stop. Do not re-fire it -
a deploy that silently ran twice is worse than one that didn't run.

### 4. Watch

```
gh run watch <id> --exit-status
```

This is the primitive; do not hand-roll a poll loop, and do not reuse `/commit`'s
`watch-build.ps1` - that one filters by `headSha`, so it would also scoop up the `checks.yml` run
sitting on the same sha and could report that run's verdict as the deploy's.

Run it via the PowerShell tool's own `run_in_background: true` and yield; you are re-invoked when
it exits. Never `Start-Process`/`Start-Job`/`&` - those detach from the harness's task tracking
and the result is lost. Tell the dev it is watching and that they can ignore it.

`--no-watch` fires and reports the run URL without waiting.

### 5. Report

- **Success**: say so, with the run URL and how long it took. If the repo's deploy has a
  verifiable public effect (a served asset hash, a version endpoint), check it actually changed
  rather than trusting a green run - a workflow can succeed and deploy nothing.
- **Failure**: show the failing step's log and stop. **Never auto-fix a failed deploy and never
  re-fire it.** `/commit`'s gated auto-fix deliberately does not apply here: that one re-pushes a
  branch, this one would re-run a release. Diagnose, then let the dev decide.

## Adding a new deployable repo

Write `.github/workflows/deploy.yml` in it with `workflow_dispatch:` and whatever that project
needs, put it on the default branch, add its secrets, done. `/deploy` picks it up with no change
here.

## Notes

- Never commit directly; the `/commit` skill owns every commit this flow makes.
- Secrets are the dev's to create. This skill never writes, prints or echoes a token.
- The taskbar button in Claude Conductor is a second surface onto this same skill: it injects
  `/deploy` into a session rather than reimplementing any of the above.
