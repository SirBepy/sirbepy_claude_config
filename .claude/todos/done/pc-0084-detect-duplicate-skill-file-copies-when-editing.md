<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Check for duplicate/mirrored skill-file copies before treating a skill edit as done

**Type:** skill-improvement

## Goal

Whenever Claude edits a skill/plugin markdown file (SKILL.md, rules file, etc.), it should verify whether that file has sibling copies elsewhere on disk (hardlinked or independent) and either confirm the edit propagated or mirror it manually - instead of discovering the gap by accident.

## Context

Hit this twice in the 2026-07-20 session (`c--Users-tecno-Desktop-Projects-zng-app` project):

- `~/.claude/skills/clockify-reconciliator/SKILL.md` and `~/.claude-personal/skills/clockify-reconciliator/SKILL.md` turned out to be hardlinked - one edit updated both, discovered only because a second `Edit` call failed with "file has been modified since read", prompting a re-read that revealed the other copy already had the change.
- The `caveman` marketplace plugin has ~10+ duplicate `SKILL.md`/rule-mirror copies across `plugins/marketplaces/caveman/` and `plugins/cache/caveman/caveman/<hash>/`, in multiple formats (`.cursor/skills/`, `.windsurf/skills/`, `plugins/caveman/skills/`, bare `skills/`). These are NOT hardlinked - editing one silently leaves the others stale. This was caught only by chance (diffing the two Claude-Code-relevant copies after finishing an edit).

No existing skill or habit checks for this before declaring an edit complete. Relevant background: [[reference_hubstaff_auto_login]] and the caveman-to-terse-replies migration both touched this (caveman plugin is now uninstalled, see [[project_terse_replies_snippet]], so the specific caveman duplication no longer matters - but the general problem will recur for any other plugin skill edited in place).

## Approach

- When about to edit a file under `~/.claude/plugins/**` or any path known to have a `~/.claude-personal` mirror: before writing, `find`/`Glob` for other files with the same basename under sibling plugin roots (`plugins/marketplaces/<name>/**` vs `plugins/cache/<name>/**`) and diff them against the target.
- If a hardlink (same inode - `ls -la` share inode number, or diff shows already-in-sync after independent edit attempts), no extra work needed.
- If NOT linked, mirror the edit to every discovered sibling copy in the same turn, not as an afterthought.
- Consider this only worth automating for plugin-internal files (`~/.claude/plugins/**`); the user's own `~/.claude/skills/**` and `~/.claude-personal/skills/**` pairing already turned out to be hardlinked, so likely lower priority there.

Alternative considered and rejected: skip this entirely and just always re-read+diff after every skill edit. Rejected because it's reactive (only catches the problem after making the change), not preventive.

## Acceptance

- Editing a plugin skill file triggers a check for sibling copies before the edit is considered "done".
- No regression: don't add this overhead to routine project-repo file edits (Dart/TS/etc.) - scope is plugin/skill markdown only.

## Notes

Low urgency - purely a process-hygiene gap, not a bug affecting Joe directly. The caveman-specific instance of this problem is now moot (plugin uninstalled), so this todo is about the general pattern for any future plugin-skill edit.
- Dropped via /cleanup-todos 2026-08-11: the caveman plugin that produced the evidence is uninstalled; remaining risk is speculative. Confirmed by dev 2026-08-11.
