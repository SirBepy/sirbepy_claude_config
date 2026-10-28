<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=3035201e -->
<!-- duplicate-checked: 350 is the PreToolUse hook on tool-call text args; this is the diff prefilter mis-scanning binary blobs. The other hits share only the words commit/line. -->
# em-dash prefilter scans text-like binaries (PDFs) and blocks the commit with no way to fix the line

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/em-dash.sh` (and therefore `prefilter-gate.sh` and the commit-guard hook's re-run) should never flag a binary file. A PDF, image or font that happens to contain the bytes `e2 80 94` is not an added prose line anyone can "fix", so the current behaviour makes such a file permanently uncommittable through `/commit`.

## Context

Observed 2026-09-12 in `wedding_invitation` (autopilot run, commit of `public/rite-of-marriage.pdf`, 31 KB): `commit-pathspec.sh` reported

```
[prefilter-gate] FLAGGED (fix the added line(s) and rerun, never overridable):
=== em-dash.sh ===
public/rite-of-marriage.pdf:110
```

Root cause: `em-dash.sh` pipes `git diff HEAD -- <files>` into its awk scanner. Git only treats a blob as binary when it finds a NUL byte in the first ~8 KB; a text-heavy PDF has none there, so git emitted the full content as `+` lines and the scan hit line 110. The gate is deliberately non-overridable (`commit-pathspec.sh` takes no `--force prefilter`), so the only exits were dropping the file or teaching git it is binary.

Workaround used in that repo: a one-line `.gitattributes` with `*.pdf binary`, committed first (`f091fb4` in wedding_invitation). After that `git diff HEAD` prints `Binary files differ` and the scan is clean. That fixes one repo and one extension; every other repo shipping a PDF/font/etc. will hit the same wall.

## Approach

In `skills/commit/em-dash.sh` (and check `comment-noise.sh` / `secret-scan.sh` for the same shape, they share `_prefilter-lib.sh`), skip files git or a cheap heuristic considers binary before scanning:

- Preferred: run `git diff --numstat HEAD -- <files>` (and `git diff --no-index --numstat /dev/null <f>` for untracked ones); a `-\t-\t<path>` row means git already calls it binary, drop it from the scan set. Then additionally treat a file as binary when the first 8000 bytes contain a NUL OR the path has a known binary extension (`pdf png jpg jpeg gif webp ico ttf otf woff woff2 mp3 mp4 zip`), because the git NUL heuristic is exactly what failed here.
- Print a one-line `skipped binary: <path>` info so a skipped file is visible, not silent.
- Rejected: making the gate overridable with `--force prefilter`. The whole point of the gate is that an em dash never rides an override; skipping binaries keeps that property.

## Acceptance

- A repo with a text-heavy PDF (reproduce with wedding_invitation's `public/rite-of-marriage.pdf` at `f1473c3`, with the `.gitattributes` line removed in a scratch worktree) commits cleanly through `commit-pathspec.sh` with no `.gitattributes` help.
- A `.md`/`.jsx` with an added em dash is still flagged (existing `hooks/test_*` or a scratch check).
- `ci/run_all.py` green.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), test-first (RED against HEAD, then GREEN).
