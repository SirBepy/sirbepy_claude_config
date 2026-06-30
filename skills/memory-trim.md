---
name: memory-trim
description: Audit the current project's Claude Code memory system, propose a cleanup plan, rate it, then execute on confirmation.
trigger: /memory-trim
---

# Memory Trim

Triggers on `/memory-trim`. Audits the project memory, proposes a plan, runs `/rate-it` on it, then executes only after the user confirms.

## Step 1 - Locate memory

Find the project memory dir. It lives at:
`~/.claude/projects/<encoded-cwd>/memory/`

The encoded CWD replaces path separators with `-` and colons with `-` (e.g. `C:\Users\foo\bar` → `C--Users-foo-bar`). On this machine the known path is `C:\Users\tecno\.claude\projects\<encoded>\memory\`. Derive it from the primary working directory shown in the session environment.

Read:
- `MEMORY.md` (the index)
- Every `.md` file in `memory/` and `memory/cold/` (if it exists)

## Step 2 - Run these checks

**A. Line count**
Count lines in MEMORY.md. Warn at 175, critical at 195+. The harness silently truncates at 200 lines, dropping everything after.

**B. Index entry length**
Flag any MEMORY.md bullet over 150 chars. Goal: one tight line per entry. The detail lives in the linked topic file, not the index.

**C. Orphaned topic files**
`.md` files in `memory/` not referenced in MEMORY.md → candidates for deletion or cold demotion.

**D. Broken links**
MEMORY.md entries that link to a `.md` file that doesn't exist on disk.

**E. Staleness**
Read each topic file. Flag entries that describe:
- A bug that's now fixed and stable
- A mid-flight project that shipped
- A workaround for something the codebase no longer does
- A one-time incident that won't recur
Use judgment - don't flag something just because it's old; flag it because it's no longer load-bearing.

**F. Hot/cold classification**
Behavioral rules (how Claude should act, things Claude gets wrong by default) → stay hot in MEMORY.md.
Technical facts (port numbers, API field shapes, single-incident fixes, resolved version quirks) → cold storage (`memory/cold/`).

**G. T0 axiom candidates**
Flag entries that meet ALL 3: (1) Claude defaults wrong without it, (2) failure is silent, (3) applies every session. These are candidates for a new `axioms.md` (max 12 items, always-loaded). Only promote if the entry isn't already in CLAUDE.md.

**H. CLAUDE.md promotion candidates**
Flag memories that apply across ALL projects (editor prefs, communication style, universal workflow rules). These belong in `~/.claude/CLAUDE.md`, not here. Don't auto-write there - flag only.

## Step 3 - Build the proposal

Print a structured report:

```
MEMORY AUDIT REPORT
===================
Index: X lines / 200 limit  [OK / WARN / CRITICAL]
Topic files: N files

CRITICAL
--------
- [issue]

TRIM INDEX ENTRY (too long)
---------------------------
- [current entry snippet]
  → [proposed shorter version]

DEMOTE TO COLD
--------------
- [filename] — [one-line reason: what kind of fact, why cold]

MARK STALE / ARCHIVE
--------------------
- [filename] — [what changed that makes this stale]

DELETE
------
- [filename] — [orphan / broken link]

T0 AXIOM CANDIDATES (for axioms.md)
------------------------------------
- [entry slug] — [which 3 criteria it meets]

CLAUDE.md PROMOTION CANDIDATES
-------------------------------
- [entry slug] — [why it's cross-project]
```

Be concrete. For every proposed change, name the file and the reason. Don't propose a change you can't justify.

## Step 4 - Rate the plan

Invoke `/rate-it` on the audit report. Ask it specifically: are the demotion/deletion calls right? Are any behavioral rules being wrongly classified as cold? Is anything missing?

If `/rate-it` scores ≥ 7: proceed to Step 5.
If < 7: show the feedback, ask the user what to adjust, loop back to Step 3.

## Step 5 - Execute (only after user confirms)

After showing the rated plan, ask: "Apply these changes?"

On confirmation:
1. Trim long index entries in MEMORY.md (rewrite in place)
2. Move demoted files to `memory/cold/<filename>` and update MEMORY.md links
3. Archive stale files to `memory/cold/` with a `stale-` prefix
4. Delete orphaned/broken-link files
5. Create `memory/axioms.md` if T0 candidates exist (write the entries, add a pointer in MEMORY.md at the top)
6. Print a summary of what changed

Never auto-write to `~/.claude/CLAUDE.md`. Surface promotion candidates to the user as a manual follow-up.
