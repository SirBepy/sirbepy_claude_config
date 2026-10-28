<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1225 (advise-only wording), 03 (scan scope), 04 (verify uninstall), 1099 (temp block counting) and 1038 (code-check gate) are other disk-doctor/gate problems, not these two references -->
# disk-doctor: windows.md/macos.md cite a gate.md check that does not exist, and blame the wrong guard for the C:\tmp block

**Type:** task
**Origin:** ai
**Summary:** The disk-doctor platform files point only at checks that exist and name the real cause of the C:\tmp removal refusal.

## Why

Found by the 2026-10-28 per-commit review of 10a76b4: windows.md and macos.md cite a gate.md section that is not committed and blame the wrong hook.

## Goal
The disk-doctor platform files point only at checks that exist, and name the real cause of the C:\tmp removal refusal.

## Context
Found by the 2026-10-28 per-commit review of 10a76b4.
- `skills/disk-doctor/windows.md:144` and `skills/disk-doctor/macos.md:34` delegate the in-use model check to `gate.md` ("Mtime alone is not last-use evidence") and say "Do not restate that check here". No committed `gate.md` has that section. On 2026-10-28 `skills/disk-doctor/gate.md` had uncommitted edits from another session (11 lines); that work may be the missing section, so check `git log -- skills/disk-doctor/gate.md` first.
- `skills/disk-doctor/windows.md:226` says `hooks/destructive-command-guard.py` blocks any `Remove-Item` naming a drive-root child. That hook's `REMOVE_ITEM_TARGET_RE` (`hooks/_destructive_guard_fs.py:30`) only matches a bare drive root or a home reference. The real refusal is the Claude Code harness built-in ("Remove-Item on system path ... is blocked"), per `refs/incidents.md:104`.

## Approach
If the gate.md section has landed, nothing to do for the first point; otherwise add it to gate.md or restore the check inline. Reword windows.md:226 to name the harness built-in.

## Acceptance
`grep "Mtime alone is not last-use evidence" skills/disk-doctor/gate.md` hits, and windows.md no longer attributes the block to destructive-command-guard.py.
