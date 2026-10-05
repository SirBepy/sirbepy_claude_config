<!-- Claim before executing: .claude/todos/.claims/1059.claim -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=111a0a1c -->
<!-- duplicate-checked: 2026-10-01; grepped this backlog for "upstream/master", "upstream-owned", "upstream-identical" (no hits) and skills/code-check for "upstream" (no hits). -->
# `/code-check` keeps flagging upstream-owned files a fork has decided never to split

**Type:** skill-improvement
**Origin:** ai

## Goal

In a repo that syncs with an upstream and has written down "do not split upstream-owned files",
`/code-check` stops filing over-length/split findings against those files, so the same finding is
not re-raised and re-decided on every run.

## Context

Surfaced 2026-10-01 in the cueline project (`C:\Users\tecno\Desktop\Projects\cueline`), its todo 36.
Cueline is a fork of `AIEraDev/Clypra` that merges upstream weekly. Two consecutive `/code-check`
passes (2026-09-26 and 2026-09-27) flagged six upstream-owned files as over-length with clean split
seams, and each was correctly classified judgment-level because no policy existed. Cueline's
`docs/decisions.md` D12 now records that policy: upstream-owned files are not split for structure
alone, because every moved line becomes a merge conflict on every future sync.

The decision being written down does not stop `/code-check` from re-flagging the files; it only
gives the reviewer something to point at. The cueline todo predicted exactly that cost.

## Approach

Options, roughly in order of preference:

1. In `/code-check`'s structural lens, before emitting a file-split or over-length finding, check
   whether the repo has an `upstream` remote and whether the file differs only slightly from it
   (`git diff --numstat upstream/master -- <path>`, or `upstream/main`). If so, and the repo
   documents a no-split rule, suppress the finding or downgrade it to a one-line info.
2. A lighter version: a per-repo opt-out list (for example a section in the project's own CLAUDE.md
   or `.claude/code-check.md`) naming paths that are exempt from size findings.

Decide how `/code-check` should find the repo's rule (a known file, a CLAUDE.md line) rather than
hard-coding cueline.

## Acceptance

- A `/code-check` run in cueline over a diff touching `src/store/projectStore.ts` does not file a
  split finding against it.
- Repos with no upstream remote behave exactly as before.
