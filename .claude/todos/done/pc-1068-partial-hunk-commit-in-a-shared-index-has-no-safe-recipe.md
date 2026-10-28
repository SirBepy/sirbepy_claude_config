<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=9, reconfirm-count=1, content-hash=06f16024 -->
<!-- duplicate-checked: 1046 is the shell redirect in the same recipe, 806 and 872 are the working-tree foreign-hunk check, 797 is positional refs; none covers committing hunks past a shared index that holds another session's staged files, or the HEAD race of a private index -->
# Partial-hunk commit in a shared index has no safe recipe

**Type:** skill-improvement
**Origin:** ai

## Goal
`skills/commit/edge-cases.md` gives a partial-hunk commit recipe that is safe in a repo whose git
index is shared with concurrent sessions (zng-app, zng-biller), and that refuses instead of
committing on top of a HEAD that moved underneath it.

## Context
Hit 2026-10-02 in zng-app (sc-56160). One file (`v2_verify_screen.dart`) held this session's hunks
plus a peer session's uncommitted hunk, and the shared index already held a THIRD session's staged
files. `edge-cases.md:15-26` ("Splitting one file across commits") commits FROM the index after
`git apply --cached`, which would have swept the third session's staged files into the commit. Its
own guard ("re-run `git diff --cached --stat` ... stop and re-isolate") just stops, with no way
forward.

The workaround used: a private index (`GIT_INDEX_FILE=.git/index-<tag>`, `git read-tree HEAD`,
`git add` own whole files, `git apply --cached --recount` own hunks, `git commit`), then
`git reset -q -- <own paths>` on the real index so its entries match the new HEAD. It works, but it
has a race: the peer session committed between `read-tree HEAD` and `git commit`. The commit
landed on the peer's new HEAD with a tree built from the OLD HEAD, so it silently reverted the
peer's whole commit (`20 files changed ... delete mode` for their new files). It was caught only
because the commit summary showed unexpected deletions, then rebuilt via a CAS `update-ref`. The
commit-guard hook passed it (no pathspec, decided gap todo 868), and `commit-pathspec.sh`'s HEAD
guard was not in the path because the private-index route bypasses that script.

## Approach
Add a "Partial hunks in a shared index" subsection to `edge-cases.md` (or a small helper,
e.g. `skills/commit/commit-hunks-private-index.sh`) that:
1. Records `base=$(git rev-parse HEAD)` first.
2. Builds the private index from `$base`, adds own files and own hunks, `tree=$(git write-tree)`.
3. `new=$(git commit-tree $tree -p $base -m ...)` then `git update-ref HEAD $new $base`. That CAS
   refuses if HEAD moved, instead of committing a stale tree on top of a peer commit.
4. Resyncs the real index entries for the committed paths with `git reset -q -- <paths>`.
5. Prints `git show --stat HEAD` and fails if it lists a path outside the declared pathspec.
Also reference it from `SKILL.md` step 8's shared-checkout notes. Check whether commit-tree needs
the commit-guard marker or a hook exemption, and record the decision.

## Acceptance
- With a peer commit landing between steps 1 and 3 (simulate with a second worktree commit), the
  recipe refuses and leaves HEAD at the peer's commit.
- With another session's files staged in the shared index, the resulting commit contains only the
  declared paths and hunks, verified by `git show --stat`.
- The shared index shows no staged entries for the committed paths afterwards.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05). Script halves: eccffe6, 5d6f7b2, 61e7fae, f582722 (tests in skills/commit/test_*.sh); doc halves in skills/commit/SKILL.md (this commit) and e9f4620.
