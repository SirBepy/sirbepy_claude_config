# Global Knowledge Vault - full conventions

Read this before the first vault write of a session (companion to `refs/memory-rubric.md`'s "read
once per session, before the first write" gate - the rubric decides ADD/UPDATE/DELETE/NONE, this
file decides vault vs native once you're already writing).

## Scope test

Cross-project facts (true regardless of which project session it is) live in the real Obsidian
vault at `C:\Users\tecno\Documents\ObsidianVault\`, not in Claude Code's per-project Auto Memory.
Would this matter in a totally different project too? If yes, vault. If it's project-local (a bug
workaround, a project-specific quirk), keep using native per-project Auto Memory as today,
untouched by this file.

## People

One file per person under `People\`, following the vault's own `Templates\Person.md` schema
(frontmatter: name, aliases, birthday, relationship, last_seen, tags; body: `## Notes` bullets,
`## Gift Ideas` block). When a name comes up, check `People\*.md` by name and `aliases` before
assuming who it is - real entries already live there (e.g. `People\Bruno Kecman.md`).
Disambiguation is structural, not semantic: distinct filenames + `aliases` + `tags` (e.g.
`[person, friend]` vs `[person, family]`) separate same-named people/companies/projects; if still
genuinely ambiguous, ask, never guess silently.

## Other facts

Preferences, hobbies, ideas go in a loose vault note following its existing free-form style (see
`Moms info.md`, `Cocktails.md`) - no rigid schema required.

Cross-project coding standards (e.g. "always do X in Flutter") belong in `~/.claude/code-style/`,
not the vault - that folder is already global and already checked on first encounter with a stack.

## Writing and backup

Write directly, same as native memory - no confirmation gate. The vault's own `obsidian-git`
plugin auto-backs-up on its own schedule; Claude never runs git commands inside this repo.
**Fallback:** if the plugin is verifiably dead (newest commit older than ~7 days AND `git status`
shows dirty files), a manual backup commit+push is allowed - message style `vault backup: <date>
(manual - obsidian-git plugin dead since <last-auto-commit-date>)` - and tell Joe the plugin needs
fixing.

## Concurrent-write discipline

The vault is shared - Joe often runs 3+ sessions at once, and nothing locks these files, so a
whole-file overwrite from a stale read silently destroys another session's write. Same CAS rule
the todos backlog already uses for PLAN.md: re-read the file immediately before every write, apply
your change to that fresh content, and keep edits line-scoped (append a bullet, edit one
frontmatter field) rather than rewriting the file from an in-memory copy. Prefer appending a dated
bullet under `## Notes` over restating the whole note. Never regenerate a person file from a
template when it already exists.
