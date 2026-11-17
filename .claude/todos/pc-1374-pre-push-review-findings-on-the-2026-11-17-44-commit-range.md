<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: the hits share only the words push/review/commit; none covers these defects -->
# Pre-push review findings on the 2026-11-17 44-commit range

**Type:** task
**Origin:** ai
**Summary:** Fix six low-severity defects the per-commit review of the 2026-11-17 push found, none of which blocked the push.

## Goal
Close each defect below, one small commit each, with a test where the code changed.

## Context
Found by the sliced `/review-unpushed` pass in the 2026-11-17 push gate (sonnet reviewers). Paths and lines are as of HEAD bba8f69 unless noted. Re-run each repro before acting: they were read off commits, not all re-run at HEAD.

1. `hooks/outbound-verify-guard.py` `read_file` (about :210-222) catches `OSError` only. A non-UTF-8 `--body-file` (a UTF-16 file from PowerShell 5.1) raises `UnicodeDecodeError` out of `detect()`, the module logs "hook error, failing open" and exits 0. One bad-file statement then un-gates every other statement chained with it: `kickoff.py comment 1 --body-file bad.md; kickoff.py comment 2 --body-file unverified.md` exited 0 in the reviewer's repro. Fix: catch `(OSError, UnicodeDecodeError)` and raise `Unverifiable`; add a test in `hooks/test_outbound_verify_guard.py`.
2. Same file, `SHELL_STRING_PREV_RE` (about :79) reads the `-c` of `rg -c` or `git grep -c` as `bash -c`, so `rg -c "kickoff.py comment" skills` is denied as a gated call (false deny).
3. Same file, variable script plus variable subcommand (`K=.../kickoff.py; python -I $K "$SUB" 1 --body-file F`) is allowed, because the variable-script branch only fires when the next token is in `KICKOFF_PROSE_COMMANDS`. Contradicts the `detect_kickoff` docstring.
4. `skills/zng-kickoff/scripts/kickoff.py`: `cmd_mine` passes `cap=500` and `search` stops silently at 500 while `next` is still present, so a large state (Done) prints a truncated list as complete. In `newer_activity`/`approval_time`, the hook records approval with millisecond precision while Shortcut stamps have second resolution, so a comment by someone else in the same second as the approval but after it is read as not newer (fails open, under 1 s window).
5. `skills/zirtue-release-backfill/SKILL.md`: line 233 says a ticket with a concrete Release moves to Testing (Gate E), while Gate E (line 323) says the move happens with no Release set. Line 364 compares `fresh_state_name`, defined nowhere in the snippet; Gate D on the line above compares `fresh['workflow_state_id'] == 500018659`. Compare Gate E by the three state ids instead.
6. `skills/disk-doctor/windows.md` line 243 still shows `AddDays(-2)` on the top-level LastWriteTime, while line 244 says the card now offers 7 days and excludes any dir holding a file written today. Line 59's metric is still `TempOver2DaysGB`. Note: the working tree held an uncommitted edit to this file when this was filed, so reconcile with it first. Also `.claude/todos/pc-1362-copy-paste-text-goes-in-fenced-code-not-blockquotes.md:5` has `**Type:** global-rule`, which the format contract does not define (`task | skill-improvement`); and `skills/recall/recall.py` `_merge_digest_bodies` drops text before the first `##` heading of an incoming body (cosmetic).

7. Code-check (structure) findings, class 3 first:
   - `hooks/outbound-verify-guard.py:78,87,~716,736`: the comment and `detect_kickoff` docstring say an unknown literal kickoff.py subcommand is gated, but line 736 skips any literal subcommand outside `KICKOFF_PROSE_COMMANDS`, so a future prose-sending subcommand passes ungated; `KICKOFF_PROSE_FREE_COMMANDS` is redundant. Decide fail-closed vs allow-by-default, then make comments and code agree.
   - `skills/grill/SKILL.md`: names "Joe" 25 times and has a multi-line blockquote (bepy-skill-creator FAIL: no hardcoded user names, one-line quote); no `disable-model-invocation: true`.
   - `skills/respawn/SKILL.md` Save step: "an unfinished item that only Joe can unblock is filed as a task todo" conflicts with the CLAUDE.md rule that physical-action blockers get no file; narrow it.
   - /grill archives (`.claude/grill/`) are allow-listed in the PUBLIC repo's `.gitignore` while the skill copies receipt quotes from transcripts and client-repo decision docs: decide whether archives may be committed at all before the first real run is pushed. No archive was in this range (fixtures only).
   Class 2: `hooks/outbound-verify-guard.py` (956 lines) could split its kickoff detector into `hooks/_outbound_verify_kickoff.py`; `skills/grill/grill_dump.py` (1601) and `kickoff.py` (1005) are over 400 lines but run under `python -I` so a sibling import needs a sys.path insert; `grill_dump.py:705 git_outcome` is only called by tests.
   Class 1 (comment fixes): `outbound-verify-guard.py:80` comment sits above `INTERPRETERS_RE` but describes `SHELL_STRING_PREV_RE`; `shell_string_kind` inlines `SUBSTITUTION_RE`; `grill_dump.py:4` docstring omits `sources.jsonl`; `skills/mega-todos/test-archive-batch.ps1:148` still names `close/_shared.ps1` as off limits; `kickoff.py:3-34` docstring omits `mine`.
   Also: `skills/grill/SKILL.md` step 2 says "sum `human_turns`" but `recall.py activity --json` returns a list (:807), so it should say count.

## Approach
Items 1 to 3 first (they are the only ones that can let an unverified post through or block a legitimate read), then 4 to 6.

## Acceptance
Each item has its repro run against HEAD, then green after the fix; `python ci/run_all.py` passes.
