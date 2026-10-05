<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=8b102c2c -->
<!-- duplicate-checked: grepped the backlog and done/ for "no newline", "@@ -1 +1", "single-line hunk". Zero hits. -->
# 1064 - foreign-hunk-check flags a one-line, no-trailing-newline file as foreign

**Type:** bug
**Origin:** ai
**Created:** 2026-10-02

## Goal

`skills/commit/foreign-hunk-check.sh` should report `clean` for a file whose whole diff is one
replaced line with no trailing newline, when the caller's own range covers that line.

## Context

Seen 2026-10-02 during `/flutter-bump` (3.47.5 to 3.47.6) in zng-app, zng-admin and zng-biller,
all three identically. `flutter.version` holds only the version string, ASCII, no trailing
newline. Its diff:

```
@@ -1 +1 @@
-3.47.5
\ No newline at end of file
+3.47.6
\ No newline at end of file
```

`commit-pathspec.sh` auto-derived `flutter.version: own-range 1-1`, and the foreign-hunk step
still printed `flutter.version: foreign-hunks-present 1-1`, so every bump commit needed
`--force foreign-hunk`. `.fvmrc` and `.vscode/settings.json` (multi-line, also no trailing
newline) came back clean in the same calls.

Likely cause, UNVERIFIED: the `@@` header omits the line count when it is 1 (`+1` rather than
`+1,1`), and the range parser may read that as a zero-length or unparsed hunk, so a 1-1 own range
never covers it. Would check the hunk-header parsing in `foreign-hunk-check.sh`.

## Acceptance

- The diff above, with `--own flutter.version:1-1`, exits 0 with `flutter.version: clean`.
- A test case for a count-less `@@ -N +N @@` header sits alongside the script's existing tests.
- `/flutter-bump` commits no longer need `--force foreign-hunk`.
