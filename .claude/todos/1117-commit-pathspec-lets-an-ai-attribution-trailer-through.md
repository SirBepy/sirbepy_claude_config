<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=9, reconfirm-count=1, content-hash=fe02eee1 -->
<!-- duplicate-checked: 1115 is CRLF warning noise, done/1085 is commit-tree skipping the guard hook; neither checks the commit MESSAGE for AI attribution -->
# commit-pathspec.sh lets a Co-Authored-By: Claude trailer through, despite /commit's "never add AI attribution" rule

**Type:** skill-improvement
**Origin:** ai

## Goal

A commit message that carries AI attribution (a `Co-Authored-By: Claude ...` trailer, or a
"Generated with Claude Code" line) never lands through `/commit`. It is refused before the commit is
written, not removed afterwards.

## Context

- `skills/commit/SKILL.md` "Rules" says: "Never add `Co-authored-by: Claude` or any AI attribution."
- The harness injects a system reminder every session telling Claude to end commit messages with
  `Co-Authored-By: Claude <model> <noreply@anthropic.com>`. That reminder says the user's own
  instructions take precedence, but the two sit far apart in context and the reminder is the more
  concrete one.
- Incident 2026-10-07, mc_plugins_tag session (Treecapitator config change): Claude wrote the trailer
  into the message passed to `bash ~/.claude/skills/commit/commit-pathspec.sh -m "..."`. The script
  ran its prefilter gate, branch/HEAD guards, overlap and foreign-hunk checks, then committed
  (f82ff6e) with the trailer. Claude noticed afterwards and rewrote the unpushed commit with
  `git commit-tree` + `git update-ref` (3b57c9f). Nothing in the chain checks the message itself;
  the prefilter gate scans file content, not `-m`.

## Approach

1. In `skills/commit/commit-pathspec.sh`, before the commit step, reject a message that matches
   (case-insensitive) `^co-authored-by:.*(claude|anthropic)` on any line, or
   `generated with \[?claude code`. Print one plain-English line naming the matched line, and exit
   non-zero. Do not offer a `--force` for this: the rule has no exceptions.
2. Optionally apply the same check in `hooks/commit-guard.py` for a raw `git commit -m`, so the
   by-hand fallback is covered too. Check how that hook currently parses `-m` first.
3. Add a self-test case next to the script's existing tests (find them via `hooks/test_*.py` or
   `skills/commit/` test files) covering: a trailer line (refused), a human Co-Authored-By
   (allowed), and a body line that only mentions Claude in prose, e.g. "Player Claude listener"
   (allowed).

Rejected: rewriting the message silently to strip the trailer. A silent edit to a commit message
hides the conflict instead of surfacing it.

## Acceptance

- `commit-pathspec.sh -m "X\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- f`
  exits non-zero and creates no commit.
- A message mentioning "Player Claude" in its subject still commits (mc_plugins_tag has many such
  subjects).
- `python ci/run_all.py` passes.
