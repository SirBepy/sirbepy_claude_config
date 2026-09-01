<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=3, content-hash=81ddb0bb -->
<!-- duplicate-checked -->
# `list_peers` has no enforcement before the first edit, only social pressure

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the pre-edit half of the `list_peers` rule enforceable, the way the pre-commit half already is.

## Context

Global `CLAUDE.md` tells the model to call `list_peers` "before editing any file another Conductor
session might also be touching, and before running `git commit`". The commit half has real teeth:
`/commit` step 7a names it as a numbered step in a procedure the model is reading at that moment.
The edit half has none - it is one clause in a long instructions block, competing with everything
else, at a moment when the model is mid-task and not reading any procedure.

Result on 2026-08-20 in `zng-app`: a session built two todos across `lib/ui/loan_request_v2/`,
called `list_peers` dutifully before committing, and never called it before the first `Edit`. A
second Conductor session was editing the same eight files the entire time. It surfaced only when
`file changed on disk` notices began arriving mid-task. Cost was roughly an hour: paused work,
ownership negotiation, stripping a peer's method out of a commit to keep it compiling, and two
extra rebuild-and-reverify cycles because the tree moved under an already-verified run.

This is the same failure shape the em-dash rule already demonstrated: a wording-only rule that
depends on the model remembering it at the right instant fails eventually, and the fix is a hook,
not stronger wording.

## Approach

A `PreToolUse` hook on `Edit`/`Write` that fires at most once per session per repo:

1. Skip entirely unless the cwd is a git repo that Conductor is hosting (no peers concept
   otherwise), and skip if the session has already been warned once - this must not nag per edit.
2. Ask the daemon whether other sessions share this `cwd`. The `list_peers` MCP tool already
   answers exactly that; the hook needs the same data from outside the model loop, so check whether
   the daemon exposes it over HTTP/IPC before assuming a hook can reach it. **If it cannot, this
   todo is not buildable as specified** - say so rather than shipping a hook that always passes.
3. Zero peers: allow silently, and mark the session so step 1 short-circuits from then on.
4. One or more peers: emit a warning naming them and the file about to be edited. Warn, do not
   block - a peer existing is common and usually harmless, and a blocking hook on `Edit` would be
   far more disruptive than the problem it prevents.

Files: `~/.claude/hooks/` for the hook, registered in `settings.json` per the `update-config`
skill's rules.

## Acceptance

- Editing a file in a repo with an active peer session produces exactly one warning naming the peer
- Editing in a repo with no peers produces no output at all
- The warning fires once per session, not per edit
- If step 2 proves impossible, this file is closed with a note recording that, not left open

## Notes

- Related and already handled: the per-project memory
  `feedback_list_peers_before_every_commit_and_push` was updated 2026-08-20 with this incident, so
  the behavioural half is recorded even if this hook is never built.
