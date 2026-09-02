<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# ui-screenshot-reminder scopes its freshness scan to the first touched file's repo

**Type:** task
**Origin:** ai

## Goal

Decide what `hooks/ui-screenshot-reminder.py` should do when one turn edits UI files in two
different repos, then make the code match the decision.

## Context

Found 2026-09-01 by `/code-check` over `0b471f0..HEAD`, Step 4, in an isolated review subagent.

`main()` computes `ui_mtime` as the newest mtime across ALL of the turn's edited UI files
(around line 197), but resolves the repo it scans for screenshots from `ui_files[0]` alone
(around line 201). So a turn that edits UI files in two repos measures freshness against a
screenshot directory belonging only to the first one.

**UNVERIFIED:** the line numbers come from the review subagent's report, not a re-read, and the
multi-repo turn was reasoned about rather than reproduced. Confirm both before changing anything.

Severity is low and should stay framed that way. This is a Stop hook that emits an advisory
reminder; it blocks nothing. The worst outcome is a reminder that fires when it should not, or
stays quiet when it should not. It is filed because the mismatch between "newest across all files"
and "repo of the first file" is the kind of half-scoped condition that reads as correct forever.

No document states what a multi-repo turn should do here, so this is not a convention breach. It is
a judgment call, which is why it is filed rather than fixed on sight.

## Approach

1. Re-read `hooks/ui-screenshot-reminder.py` and confirm the two lines actually disagree as
   described. If they do not, close this with the evidence quoted.
2. Decide between: group the UI files by repo and evaluate each group independently (most correct,
   most code); use the repo of the NEWEST UI file rather than the first (one-line, matches how
   `ui_mtime` is already computed); or declare multi-repo turns out of scope and say so in a
   comment naming the limitation.
3. Whichever is chosen, the reason belongs in the code as a short comment, since the next reader
   will otherwise re-find this same mismatch.

## Acceptance

- The freshness scan's repo scope and the mtime it compares against are derived consistently, or a
  comment states deliberately why they are not.
- `hooks/test_ui_screenshot_reminder.py` passes, with a case covering whichever multi-repo
  behaviour was chosen.
- `python ci/run_all.py` exits 0.
