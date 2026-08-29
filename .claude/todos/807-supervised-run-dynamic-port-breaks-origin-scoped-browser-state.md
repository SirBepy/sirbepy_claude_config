<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=13c2710e -->
<!-- duplicate-checked -->
# supervised-run's dynamic port silently orphans origin-scoped browser state (localStorage)

**Type:** skill-improvement
**Origin:** ai

## Goal

Have `skills/supervised-run/SKILL.md` warn that its default dynamic-port assignment breaks any
client app that persists state in `localStorage`/`sessionStorage`/IndexedDB, and document the pin
pattern for a plain Node server reading `process.env.PORT`.

## Context

Hit 2026-08-23 in the `honeymoon-tools` project (ObsidianVault session). A static file server
(`src/serve.mjs`, `process.env.PORT`) backs a single-page deck whose "shortlist" feature is stored
in `localStorage`, scoped per-origin (host+port). It was first run standalone on port 42180 and a
13-hotel shortlist with notes/ranks was built up over several sessions.

Later, `sv.ps1 ensure -Project honeymoon-tools -Cmd "npm run serve"` started the same server through
the supervisor, which assigned a new random port (42181). Same server, same code, same browser -
different origin, so the shortlist read back empty. It looked exactly like data loss; the data was
never touched, just orphaned under a port nothing was pointed at anymore.

The Port table in `SKILL.md` covers how to template `{PORT}` into a tool's own flag, but says
nothing about the case where the port *itself* is part of the app's persistence key and needs to
stay stable across restarts - that only surfaces once a dev's client-side state has gone missing
and someone has to reason backward from "localStorage is origin-scoped" to "the port changed."

## Approach

- In the Port table's "Node server reading `process.env.PORT`" row (or a new note near it), flag
  that dynamic-port apps with client-side persisted state (localStorage/sessionStorage/IndexedDB)
  need a PINNED port across restarts, not the default dynamic one - the port is effectively part of
  the storage key.
- Document the pin pattern for a `process.env.PORT`-reading server, since there's no `{PORT}` flag
  to override: `-NoDynamicPort` won't help here (the tool has no port flag either); the workaround
  is wrapping the entry command to set the env var before import, e.g.
  `node -e "process.env.PORT='<port>';import('./src/serve.mjs')"`.
- Consider whether `sv.ps1 ensure` should accept an explicit `-Port` param that pins
  `use_dynamic_port: false` plus a caller-supplied value, instead of requiring the wrapper-command
  workaround.

## Acceptance

- A dev serving a localStorage-backed static app through `/supervised-run` sees the pin caveat
  before first restarting it, not after client-side state looks like it vanished.

## Notes

Full incident, fix, and the pinned port in use: `Honeymoon.md`'s "The deck, 2026-08-23" section in
the ObsidianVault repo (not this repo - cross-referenced for context only).

- Renumbered from `410` to `807` on 2026-08-26. Two different todos were filed as `410` in the same
  55-todo bulk commit `95d47fd`, so neither had seniority; this one moved because the other is
  referenced by filename from `782` and moving it would have broken that link. Nothing else in the
  repo referenced this file. An unqualified "do todo 410" was ambiguous while the collision stood,
  which is what `claim-todo.ps1`'s and `complete-todo.ps1`'s `-Slug` disambiguator exists for.
