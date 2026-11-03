<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1025 (done) is about printing derived ranges on refusal, 1026 about git add defeating the untracked exemption, 1004/1033/105 about other flags and deletions. This one is a caller claiming a whole file as its own range, which makes the foreign-hunk check pass by definition. -->
# `--own-range <file>:1-9999` silently defeats commit-pathspec's foreign-hunk check

**Type:** skill-improvement
**Origin:** ai
**Summary:** commit-pathspec warns visibly when a caller claims a whole file as theirs, instead of reporting it clean while another session has changes in it.

## Why

On 2026-10-24 in dashboard-a, a commit using a whole-file range swept in another chat's uncommitted removal while the check printed "clean".

## Goal

Stop `skills/commit/commit-pathspec.sh` from reporting a shared file "clean" when the caller claimed the whole file
with `--own-range <file>:1-9999` while another session has uncommitted hunks in it.

## Context

- dashboard-a, 2026-10-24: two design chats edited `docs/design/demo.html` in one checkout. The opened-mail chat
  committed with `--own-range docs/design/demo.html:1-9999` (its handover prompt told it to), the script printed
  `[foreign-hunk-check] clean`, and commit 1f014dd swept in the other chat's uncommitted removal of a hover card.
  The other chat noticed and documented it in a0a55c0.
- A whole-file own-range makes every hunk "own" by definition, so the check cannot fire. Callers reach for it because
  computing real line ranges by hand is tedious.

## Approach

In `commit-pathspec.sh`: when an own-range covers the whole file (start 1, end at or past the file length), print
every hunk header of that file and a warning that the range claims the whole file, so the caller sees foreign hunks.
Also update `skills/commit/SKILL.md` so it never recommends `1-9999` for a file other sessions may be editing.

## Acceptance

A test in the commit skill's suite creates a dirty file with a foreign hunk, runs the script with
`--own-range <file>:1-9999`, and gets a visible warning instead of a bare `clean`.

## Notes

- Fixed in 7c93ad4 (whole-file --own-range now warns and lists hunks).
