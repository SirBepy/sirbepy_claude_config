<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=5, reconfirm-count=2, content-hash=87b1bdab -->
# supervised-run: wire the built-in /run skill's handoff so it finds the supervisor

**Type:** skill-improvement

## Goal

Claude Code's built-in `/run` skill ("Launch and drive this project's app to see a change
working... First looks for a project skill that already covers launching the app;
otherwise falls back to built-in patterns per project type") does not currently know
about `/supervised-run` or `server_supervisor` - so when `/run` fires for a project with
no dedicated project-level launch skill, it falls back to its own built-in patterns
(spawning the server directly) instead of routing through the supervisor, defeating the
whole point of `/supervised-run`'s no-orphans guarantee for that entry path. Wire a
handoff (a CLAUDE.md line, or a small shim skill) so `/run` finds and uses the supervisor
instead of launching servers outside it.

## Context

`skills/supervised-run/SKILL.md` (as of 2026-08-01) is a fully-specified skill: discovers
the supervisor's API token/port under `%APPDATA%\com.sirbepy.server-supervisor\supervisor\`
(Step 1), probes health (Step 2), lists existing processes before creating a new one
(Step 3), starts via `POST /run` with dynamic-port templating (Step 4), and falls back to
running the server directly ONLY if the supervisor is unreachable (documented in its own
"Fallback" section: "Never block on the supervisor being up... Do NOT try to launch the
supervisor app yourself").

The built-in `/run` skill (per its own description, listed in this environment's
available-skills) explicitly says: "First looks for a project skill that already covers
launching the app; otherwise falls back to built-in patterns per project type (CLI,
server, TUI, Electron, browser-driven, library)." `/supervised-run` is a GLOBAL
(`~/.claude/skills/`) skill, not a project-level one - so `/run`'s "first looks for a
project skill" check does not surface it, and `/run` silently falls through to its own
built-in server-launch pattern, bypassing the supervisor and reintroducing exactly the
orphan-process risk `/supervised-run` exists to prevent (per the global CLAUDE.md
"Process Hygiene" section's "Non-negotiable" framing).

## Approach

Two possible fixes - evaluate both when picking this up, pick based on what actually
changes `/run`'s behavior (this todo doesn't presume which works, since `/run`'s internal
skill-discovery logic isn't visible from this repo):

1. **CLAUDE.md line.** Add an explicit instruction to the global CLAUDE.md (or a
   per-project CLAUDE.md, if `/run`'s "project skill" check reads project-level CLAUDE.md
   content as part of its search) stating that long-lived server launches should go
   through `/supervised-run`, worded so it's discoverable by whatever `/run` uses to look
   for "a project skill that already covers launching the app" - test whether `/run`
   picks this up in practice (invoke `/run` on a project with no dedicated launch skill,
   confirm via the supervisor's `GET /procs` list whether the launched server actually
   registered there).
2. **Shim skill.** If a CLAUDE.md line doesn't change `/run`'s behavior (e.g. because
   `/run`'s "project skill" search is scoped to literal skill files, not CLAUDE.md prose),
   create a minimal project-level (or global, if that's what `/run` actually searches)
   shim skill whose only job is "launching this app means: invoke `/supervised-run`" -
   named/described so `/run`'s own discovery heuristic picks it up as "a project skill
   that already covers launching the app."

Whichever approach works, verify empirically rather than assuming - `/run`'s internal
discovery mechanism is not visible from this repo's files, so this has to be confirmed by
actually invoking `/run` against a real project and checking the supervisor's process
list afterward.

## Acceptance

- Invoking `/run` on a project with no dedicated project-level launch skill results in
  the server appearing in `GET http://127.0.0.1:<port>/procs` (i.e. it went through the
  supervisor), not a bare orphaned background process outside supervisor tracking.
- The fix is documented (CLAUDE.md line or shim skill file) so future sessions don't need
  to rediscover this.

## Notes

- completed, commit c2dca59. Documentation only: /run is a built-in harness skill whose internals are not visible from this repo, so the handoff is written with the /run side marked unverified and a GET /procs verification recipe given.
