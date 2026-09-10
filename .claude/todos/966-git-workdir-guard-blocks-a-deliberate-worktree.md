<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=9, reconfirm-count=1, content-hash=f7ed71aa -->
<!-- duplicate-checked: grepped the backlog and done/ for "workdir-guard", "worktree" and "bypass". 948 covers DETECTING a bare `cd` that drifts the cwd; 946 covers removing a worktree safely. Neither covers the guard firing on a worktree the session created on purpose. -->
# git-workdir-guard blocks a deliberate worktree, so the bypass gets used as routine

**Type:** skill-improvement
**Origin:** ai

## Goal

Let `hooks/git-workdir-guard.py` tell a session's own git worktree apart from a cwd that drifted
somewhere else, so the documented workflow of building in a worktree does not require setting
`CLAUDE_GIT_WORKDIR_GUARD_BYPASS=1` by hand.

## Context

Several projects have a memory prescribing a git worktree as the normal way to build while the dev
has the app running (countoff's `build-in-a-worktree-while-joe-tests`: "work in a git worktree with
its own dev server on a different port, and merge to `main` in one go at the end"). Following that
instruction puts the shell in `<project>-wt` while the session's project is `<project>`, which is
exactly the shape the guard treats as drift.

Observed 2026-09-06 in the countoff viewing-as session, working in
`C:\Users\tecno\Desktop\Projects\countoff-wt` on branch `viewing-as`:

```
[git-workdir-guard] Blocked: this git write command's shell is inside
'C:/Users/tecno/Desktop/Projects/countoff-wt', but this session's project is
'C:/Users/tecno/Desktop/Projects/countoff' - the shell cwd likely drifted from an earlier `cd`.
```

Two things make this worth fixing rather than living with:

1. **It is inconsistent.** The session's FIRST commit in that worktree went through untouched; a
   later commit in the same directory was blocked. So the guard cannot be relied on either way, and
   a session cannot predict which commits need the bypass.
2. **The bypass becomes habitual.** The only way past it is
   `CLAUDE_GIT_WORKDIR_GUARD_BYPASS=1`, and a session that has set it once for a legitimate reason
   carries that habit into the next block, which may be a real drift. The guard exists because a
   wrong-repo push published silently on 2026-09-02; a bypass that gets typed reflexively is worth
   less than one that is never needed.

The information needed to tell the two apart is already available with no guesswork:
`git -C <cwd> rev-parse --git-common-dir` inside a linked worktree resolves to the MAIN checkout's
`.git`, so a worktree of the session's own project is identifiable without matching on directory
names or a `-wt` suffix.

UNVERIFIED: the hook's current logic has not been read this session; the quoted message above is
its live output, not its source. Read `hooks/git-workdir-guard.py` before editing to confirm where
the comparison happens and whether a common-dir check fits its existing shape.

## Approach

- Read `hooks/git-workdir-guard.py` and find the cwd-vs-project comparison.
- Before blocking, resolve both sides' `--git-common-dir` (absolute, normalised). If they are equal,
  the shell is in a linked worktree of the session's own repo: allow, and print one line naming the
  worktree and its branch so the choice stays visible rather than silent.
- If they differ, block exactly as today.
- Add a case to the hook's own `hooks/test_git_workdir_guard.py` (create it if absent, following the
  existing `hooks/test_*.py` shape) covering: same repo via worktree = allowed, different repo =
  blocked, non-repo cwd = blocked.
- Leave the env-var bypass in place; this only removes the routine reason to reach for it.

## Acceptance

- `python hooks/test_git_workdir_guard.py` passes, including the new worktree case.
- `python ci/run_all.py` passes.
- Manual check: `git worktree add ../<repo>-wt -b scratch`, then a `git commit` from inside it
  with no bypass env var set, succeeds and prints the worktree notice; a `git commit` run from an
  unrelated repo's directory is still blocked.

## Notes

Filed from a countoff session, per global CLAUDE.md: a finding about the `~/.claude` tree belongs in
this backlog, not the surfacing project's. No peer sessions were active in either repo at filing
time (`list_peers` empty, 2026-09-06), which is a weak signal rather than proof, so claim before
executing as usual.

The same session also lost seven screenshots to `git worktree remove --force`, which deletes
gitignored files along with everything else. That half is recorded in countoff's own
`build-in-a-worktree-while-joe-tests` memory and overlaps todo 946's surface; it is deliberately
not re-filed here.
