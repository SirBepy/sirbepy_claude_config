<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Check the people-memory for a stated language before defaulting to Croatian

**Type:** skill-improvement

## Goal

Enforcement gap in `~/.claude/refs/copy-paste-format.md`'s "Language matching" section: drafted
a Croatian teammate message for Peter (sc-54802, 2026-08-06), even though
`memory/reference_zng_people.md` already states "Peter ... Communicates in English." Joe had to
correct it live.

## Context

`copy-paste-format.md` says messages to teammates "default to casual Croatian with English tech
terms left as-is ... mirror the tone of Joe's Slack history" - a blanket default with no
instruction to check per-person overrides first. The fact that Peter is English-only was
already correctly memorized; the miss was applying the blanket rule without cross-checking the
per-project people memory before drafting.

## Approach

Update `copy-paste-format.md`'s "Language matching" section (or add a one-line pointer) to check
the project's people/contacts memory (e.g. `reference_zng_people.md` for zng-*) for a stated
language preference for the specific recipient BEFORE applying the Croatian-default rule for a
teammate message. Only fall back to the Croatian default when no per-person override exists.

## Acceptance

Future teammate-message drafts check for a stored per-person language preference first; Peter
(and anyone else marked English-only) never gets a Croatian draft again.

## Notes

- Relocated from `61` in `zng-admin` via /cleanup-todos 2026-08-13: it edits `~/.claude/refs/copy-paste-format.md`, a global reference file.
- Re-verified 2026-08-13: `copy-paste-format.md:35` still carries the blanket Croatian default with no per-person override check. Fix has not landed.
- Done 2026-08-13. refs/copy-paste-format.md's teammate-message bullet now checks the recipient's People\<Name>.md in the Obsidian vault (or a project's own people memory) for a stated language preference before falling back to the Croatian default. Checked the vault schema first: Templates\Person.md has NO language field and a grep of People\*.md found no language notes, so the check points at the free-form ## Notes bullets, which is where the original incident's fact was actually recorded. Deliberately did not invent a new frontmatter field.
