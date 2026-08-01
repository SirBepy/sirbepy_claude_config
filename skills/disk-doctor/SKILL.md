---
name: disk-doctor
description: Use when Joe asks what to delete or how to free disk space. Repeatable cleanup scan, advise-only (Claude never deletes).
argument-hint: "(no args - just scan and advise)"
---

# /disk-doctor — Self-Improving Disk Cleanup Advisor

OS-aware cleanup scan. You **advise**, never delete - Joe runs the delete commands. The actual scan logic, scan commands, NEVER-TOUCH / KNOWN-SAFE lists, and SCAN LOG all live in a per-platform file. This file is just the router.

## Step 1 — Detect the platform

The environment block at session start states the platform (`win32` = Windows, `darwin` = macOS).

## Step 2 — Load and follow the matching platform file

- **Windows (`win32`)** → Read `windows.md` (in this skill folder) and follow it exactly.
- **macOS (`darwin`)** → Read `macos.md` (in this skill folder) and follow it exactly.
- Any other OS → tell Joe there is no platform file yet and offer to scaffold one from an existing file.

Each platform file is fully self-contained: it owns its scan commands, output rules, self-improvement confirmation gate, and its own NEVER-TOUCH / KNOWN-SAFE / SCAN LOG sections.

## Step 3 — Self-improvement edits go in the platform file

When invoked as `/disk-doctor`, any proposed NEVER-TOUCH / KNOWN-SAFE / SCAN LOG additions are appended to the **platform file you loaded** (`windows.md` or `macos.md`) via that file's confirmation gate. Never edit this router file for scan findings.
