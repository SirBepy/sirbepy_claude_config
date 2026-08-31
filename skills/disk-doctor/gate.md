# disk-doctor: confirmation gates

Two independent gates, shared by `windows.md` and `macos.md`. Neither is optional and neither
substitutes for the other.

## Delete-confirmation gate (required before ANY delete/uninstall runs)

Confirmed with Joe 2026-08-29: Claude may run a delete/uninstall command itself (not just hand it
to Joe), but ONLY per-item through the `mcp__cc_conductor__ask_user_question` tool - never on a
bare chat "yes"/"go ahead", and never a standing grant that covers future items or a whole batch.
Each item needs its own fresh approval, even within the same session, even if Joe approved a
similar item minutes earlier.

- One question per delete candidate (or a tightly related group Joe would obviously treat as one
  unit, e.g. "these 30 files from the age-based sweep") - never fold unrelated candidates from a
  ranked report into a single question.
- The question must name the exact path(s), size, and the exact command about to run - Joe is
  approving that specific command, not a category.
- NEVER-TOUCH entries (below, in the platform file) are never offered as an option, regardless of
  anything Joe says in the same conversation - if Joe asks for one anyway, say why it's off the
  table instead of asking.
- Only the approved item's exact command runs. A rejected or ignored item is left for Joe to
  handle himself, and is not re-asked later in the same report without new information.
- After running it, verify independently (`Test-Path`, registry check, etc. per the gotcha above)
  before reporting success - never trust the command's own exit code.

**This gate has no mechanical enforcement, and you should read it as the only thing standing
between a decision and a deleted file.** Verified 2026-08-29: `hooks/destructive-command-guard.py`
covers `Remove-Item -Recurse -Force` only when it targets a drive root or a home reference, plus
mkfs/dd/chmod-777/git-reset-hard/git-clean-f/SQL-delete/diskpart. An ordinary scoped
`Remove-Item`, `Clear-RecycleBin`, `cleanmgr`, `docker system prune` or an uninstaller matches no
tier, and `settings.json` runs `defaultMode: auto`, so none of them prompt either. Wiring the
enforcement is todo `835`.

## Platform-file edit confirmation gate

Required before either platform file is edited with a new SCAN LOG / KNOWN-SAFE / NEVER-TOUCH entry.

Output this exact format and wait for explicit YES before writing anything:

```
## PLATFORM-FILE-EDIT -- reply YES to apply
+ [SECTION-NAME] exact line to be added
```

- `SECTION-NAME` must be one of: `SCAN LOG`, `KNOWN-SAFE`, `NEVER-TOUCH`
- Claude resolves the section name to the matching header in the platform file being edited and appends the line there
- The `## PLATFORM-FILE-EDIT` sentinel line is required and must be reproduced verbatim
- Only lines beginning with `+` are written to the platform file
- No prose above or below the block
- A single gate block may contain multiple `+` lines targeting different sections
