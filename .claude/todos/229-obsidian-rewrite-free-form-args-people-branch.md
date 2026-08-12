<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=472b3b3f -->
# Rewrite /obsidian: free-form arg parsing, People/ branch, vault-root daily notes

**Type:** skill-improvement

## Goal

Replace `skills/obsidian/SKILL.md`'s rigid Step 3 `AskUserQuestion` menu with free-form
natural-language arg parsing (matching the project convention documented in the global
CLAUDE.md's "Free-form slash command args" preference), add `People/` as a first-class
workflow branch, and confirm/finish the vault-root daily-notes migration everywhere the
skill still assumes a `Journal/` folder.

## Context

SHELVED by Joe on 2026-08-01 as the largest item in a skill-audit backlog - out of scope
for that session, filed here for later pickup.

Current `skills/obsidian/SKILL.md` (as of 2026-08-01), Step 3 (lines 20-27):

```
## Step 3 - Ask what the dev wants

Use AskUserQuestion with these options:
- Plan or brainstorm a project
- Add a ticket
- Pick up a ticket
- Quick capture to Inbox
- Update today's journal
```

This forces a picker every invocation instead of parsing what the dev already said
(e.g. `/obsidian add a ticket to CUT: fix the login flow` should skip straight to the
"Add a ticket" workflow with the project and title already known).

**People/ branch:** the global CLAUDE.md (`~/.claude-personal/CLAUDE.md`, "Global
Knowledge Vault" section) already documents a People workflow - one file per person
under `People/`, following `Templates/Person.md` (frontmatter: name, aliases, birthday,
relationship, last_seen, tags; body: `## Notes` bullets, `## Gift Ideas` block) - with 20
person files already living in the vault (e.g. `People/Bruno Kecman.md`). `/obsidian`'s
own SKILL.md has no workflow branch for this at all - Claude currently has to
reverse-engineer the People convention from the global CLAUDE.md on the fly instead of
the skill file documenting it as a first-class option alongside "Plan or brainstorm a
project" / "Add a ticket" / etc.

**Daily notes at vault root:** partially done already. "Update today's journal" (SKILL.md
lines 84-89) already says: `Open <YYYY-MM-DD>.md at the vault root (not Journal/ - that
folder was abandoned 2026-05-03; daily notes live at vault root now)`. Confirm no other
step (e.g. "Pick up a ticket" step 2's `Grep Journal/ for mentions`, line 63) still
assumes the old `Journal/` folder path, and fix any that do.

## Approach

1. Read `skills/obsidian/SKILL.md` in full (current version, ~90 lines) and the vault's
   own `C:\Users\tecno\Documents\ObsidianVault\CLAUDE.md` (source of truth per Step 1) for
   folder structure/naming/templates before changing anything.
2. Replace Step 3's `AskUserQuestion` menu with a free-form parse: infer the intended
   workflow (plan/brainstorm, add ticket, pick up ticket, quick capture, journal update,
   or the new People workflow) from what the dev already typed after `/obsidian`. Fall
   back to the `AskUserQuestion` menu only when genuinely ambiguous (dev typed bare
   `/obsidian` with no further text, or the text doesn't clearly map to one workflow).
3. Add a "People" workflow section (parallel structure to "Add a ticket" /
   "Quick capture to Inbox"): create/update a `People/<Name>.md` file from
   `Templates/Person.md`, following the disambiguation rule already in global CLAUDE.md
   (distinct filenames + `aliases` + `tags` separate same-named people; ask if still
   ambiguous, never guess silently). Add "Update a person" and "Add a person" as two
   distinct free-form-parseable intents (a bare "add a gift idea for X" should append to
   an existing file's `## Gift Ideas` block, not recreate the file).
4. Fix the `Grep Journal/` reference in the "Pick up a ticket" workflow (line 63 in the
   version read above) to grep vault-root daily notes instead, consistent with the
   already-fixed "Update today's journal" workflow.
5. Re-check every other step for a stale `Journal/` assumption before calling this done.

## Acceptance

- `/obsidian <clear free-text request>` no longer stops on `AskUserQuestion` when the
  dev's text already names a workflow and enough detail to act (project, title, person
  name, etc.) - it proceeds straight into that workflow.
- `/obsidian` with no further text, or genuinely ambiguous text, still asks via
  `AskUserQuestion` (menu now includes "Manage a person" as a 6th option alongside the
  existing 5).
- A People workflow section exists in SKILL.md with create/update sub-flows, following
  `Templates/Person.md`'s schema and the disambiguation rule from global CLAUDE.md.
- No remaining `Journal/`-path reference anywhere in `skills/obsidian/SKILL.md` (grep the
  file for `Journal/` and confirm zero hits, or that any hit is intentionally historical
  prose explaining the 2026-05-03 migration, not an active instruction).

## Notes

The vault's own `obsidian-git` plugin is separately known to be dead since 2026-06-11
(manual backup committed 2026-08-01) - that is a DIFFERENT, unfiled problem (git-plugin
health, not skill behavior) and is explicitly out of scope for this todo. Do not fold a
plugin fix into this rewrite; if picked up together, treat them as two separate commits.
