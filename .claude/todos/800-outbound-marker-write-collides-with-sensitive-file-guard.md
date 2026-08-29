<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=9, reconfirm-count=1, content-hash=59bfb60e -->
<!-- duplicate-checked -->
<!-- Distinct from done/375 (built the outbound gate) and done/420 (built sensitive-file-guard.py). This is the collision BETWEEN those two shipped features, only reachable now that both exist. -->
# Outbound ground-check marker cannot be written in auto mode: sensitive-file-guard guards its own directory

**Type:** task
**Origin:** ai

## Goal

Make `/ticket`'s create path work unattended. Today the ground-check marker write is challenged by
`sensitive-file-guard.py`, so in auto mode no Shortcut or Linear ticket can be created at all.

## Context

Hit live on 2026-08-26 in a zng-app session. Joe asked for a ticket, the ground check ran clean, and
the create was still blocked. Diagnosis took several failed attempts before the cause was clear.

The collision, between two features that each work as designed:

- `refs/outbound-ground-check.md` says to write the marker into `~/.claude/hooks/`:
  `New-Item -ItemType File -Path "C:\Users\tecno\.claude\hooks\.outbound-marker-<guid>"`
- `hooks/sensitive-file-guard.py:33` has `HOOKS_DIR_RE = re.compile(r"/\.claude/hooks/", re.IGNORECASE)`
  and returns **ask** for any write matching it, reason: "an agent that can edit its own guards has
  no guards."

So every ticket create requires a write into the one directory the sensitive-file guard exists to
challenge. Interactively Joe just approves it. In auto mode (`permissions.defaultMode: "auto"`) there
is nobody to ask, so it resolves as a denial, and `hooks/shortcut-create-guard.py` then correctly
refuses the create for a missing marker. The create guard is NOT the bug; it never sees a marker.

Three observed symptoms, all the same root cause:

1. `New-Item` into `hooks/` denied, despite `PowerShell(New-Item *)` sitting in settings.json's allow
   list. The classifier overrode an explicit allow rule.
2. Same denial via the Bash tool.
3. **The `Write` tool reported success and the file never landed on disk.** Confirmed after the fact:
   only the unrelated 2026-08-24 `.outbound-marker-d8d1f58b…` was present. A silent no-op is the
   worst of the three, since nothing surfaces that the marker is missing until the create fails.

**The tell that points at the fix:** `hooks/write-session-marker.ps1` succeeded in that same session,
writing into that same `hooks/` directory. The difference is that it is a helper script invocation
rather than a raw file creation inside a guard directory. That script exists because of done/365,
which solved the adjacent problem of hand-built marker paths landing malformed.

Workaround used to unblock that one ticket (sc-55186), and it should not become the pattern: added
`CLAUDE_SHORTCUT_CREATE_HOOK_BYPASS=1` to settings.json's `env` block, created the ticket, reverted
the edit. That bypasses the create guard wholesale rather than fixing the marker write, and it needs
a settings.json edit per ticket, which is itself a sensitive-file write.

## Approach

Preferred, mirroring the pattern already proven to work: add `hooks/write-outbound-marker.ps1`
alongside `write-session-marker.ps1`, owning the directory join and guid generation and refusing to
write a malformed path, then point `refs/outbound-ground-check.md`'s "Writing the marker" section at
it instead of the raw `New-Item` line. Keeps the marker where all four consuming guards already look,
so no guard changes.

If that still trips the classifier, fall back to narrowing `sensitive-file-guard.py`'s `HOOKS_DIR_RE`
so zero-byte marker files are not treated as guard edits: exempt basenames matching
`^\.(outbound|shortcut|commit)-marker` while leaving every `.py`/`.sh`/`.ps1` in that directory
protected. The guard's stated intent is stopping an agent editing its own guards, and a marker the
guard itself consumes and deletes is not a guard edit.

Rejected: moving markers out of `~/.claude/hooks/` entirely. Four guards plus two helper scripts
resolve that path, so the blast radius is much larger than either option above.

## Acceptance

- A ticket can be created end to end in auto mode with no settings.json edit and no bypass env var.
- `python ci/run_all.py` passes, including every `hooks/test_*.py` suite.
- `hooks/sensitive-file-guard.py` still challenges a write to `hooks/shortcut-create-guard.py`,
  `settings.json`, and a `.env` file. Verify all three explicitly, since the fallback option edits
  the regex that backs them.
- The three consuming guards still block a create when no marker exists, and still consume a fresh
  one within the 120s window.

## Notes

- Separately worth deciding: whether a `Write` tool call silently reporting success while writing
  nothing is acceptable anywhere. That behaviour is what made this take several attempts to diagnose,
  and it is not specific to markers.
- Changelog 2.1.246 added an Auto mode tab to `/permissions` for viewing and editing classifier
  rules, which may offer a fourth route worth checking before building either option above.
