<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/815 and done/485 are both about step 6's git-log fetch (staleness
mid-run, and --all branch scoping); neither touches working-tree state - this is about real work
that has no commit at all yet, which git log can never see regardless of flags or timing -->
# clockify-reconciliator step 6 only sees committed work; uncommitted edits in a configured repo are invisible

**Type:** skill-improvement
**Origin:** ai

## Goal

Step 6's gap detection should also flag real uncommitted work in a configured repo, not just rely
on the dev happening to mention it.

## Context

2026-09-24, zng-app, `/clockify-reconciliator zirtue` for "today and yesterday". Step 6 ran
`git log --all --author=... ` against all 4 configured repos (`zng-app`, `zng-admin`, `zng-api`,
`zng-biller`) and correctly found zero commits in `zng-admin` for the window, so the first
proposed plan had no zng-admin entries at all. The dev caught it: "are you looking at zng-admin? i
worked on zng-admin today." `zng-admin` in fact had ~11 modified/new files with mtimes clustered
15:26-16:54, real feature work (multi-locale landing page URLs for biller group deeplinks) that
had simply never been committed yet. Only found once the dev flagged it, via `git status --short`
+ file mtimes as a rough time bound.

Step 6 as written cannot catch this class of gap: `git log`, with or without `--all`, only ever
sees commits, and a real work session can run long past when the skill is invoked without a commit
existing yet.

## Approach

In `SKILL.md` step 6, alongside the `git log` pass per configured repo, add a lightweight
`git status --short` check per repo. If it reports any modified/untracked files:

- Note the finding (file list, or just a count for a noisy repo) as a candidate gap, distinct from
  a commit-backed one - flag explicitly that it has no commit trail, only file-mtime evidence.
- Use the modified files' mtimes (oldest and newest in the dirty set) as a rough time-bound
  hypothesis for step 6a's gap detection, the same way it already infers boundaries for a
  zero-entry day from commit clustering.
- Surface it in the step 9 proposal the same way a commit-backed gap is surfaced, but the backing
  column should say "uncommitted, file mtimes" rather than naming a sha - this is weaker evidence
  than a commit and should read that way to the dev.
- Never silently skip a repo just because its `git log` pass came back empty - that emptiness is
  exactly what makes real uncommitted work invisible today.

## Acceptance

- A repo with uncommitted changes and no commits in the window still produces a candidate gap
  entry in step 9's proposal, sourced from file mtimes and labeled as such.
- A repo with genuinely nothing going on (clean tree, no commits) still produces nothing, so this
  doesn't turn into noise on every run.

## Notes

- Reproduced 2026-09-25, zng-app, Zirtue week Sep 21-25. Friday had exactly one daytime commit
  (`08df2ca` 14:35:03) and a dirty `zng-app` tree (`.gitignore`, `e2e/lib/fixtures.js`,
  `macos/Flutter/GeneratedPluginRegistrant.swift`). Step 8a's in-flight rule capped Friday at
  `14:15-14:55`, correctly refusing to guess the tail, so Friday logged **1h 25m** on a working day and
  the week landed 2h short of the 30h target.
- That is the right call under the current rules, but it shows the cost: the dirty tree was visible in
  `git status` the whole run and was never consulted as evidence, so the only honest option left was to
  under-log and defer. A mtime-bounded candidate gap from the dirty set is exactly what would have let
  the dev approve or reject the real tail instead.
- **2026-09-30, zng-app, Zirtue week Sep 28-Oct 4 (Reconstruction mode, empty week).** The Approach
  section's `git status --short` fix would not have caught this run's real gap either - two classes
  of work sit even further outside it:
  1. Work staged in a completely separate worktree (`zng-admin-followup`, per that repo's own todo
     73 handoff file), not the main checkout `git status --short` would run against.
  2. Work with zero file diff at all: ticket triage on sc-55910, filing the blocking ticket
     sc-56125, e2e screenshot verification. Nothing staged, nothing committed, nothing for any git
     command to find.
  Both only surfaced by grepping this session's own AI chat transcripts
  (`~/.claude-personal/projects/<sanitized-cwd>/*.jsonl`) for every configured repo, filtering to
  the reconciliation window's dates, and reading whatever todo/handoff files the sessions
  referenced. The dev had to explicitly ask ("try and see with other chats if there was smth
  better") before this happened - the run's own first pass, evidence sources limited to git log,
  produced a plan that undercounted a full afternoon (40min proposed vs ~6h real). Widen this
  todo's Approach to include a transcript sweep per configured repo (session start/end times
  overlapping the window, cross-referenced against any todo files the session wrote), not just
  `git status --short` - the latter is necessary but no longer sufficient.
