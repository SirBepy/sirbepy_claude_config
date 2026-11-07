# Clockify: script the configured-repo chat windows, minus idle-on-card waits

<!-- duplicate-checked: hits pc-1009 (uncommitted edits), pc-1048 (phosphor stylesheet), pc-1057 (per-repo commit counts), pc-1178 (commit lock) share vocabulary only; none covers chat windows or card-wait detection -->

**Type:** skill-improvement
**Origin:** ai
**Summary:** Give `/clockify-reconciliator` a script that lists the CONFIGURED repos' own chat activity windows per local day and subtracts stretches where a chat sat waiting on an unanswered question card, so every run stops hand-rolling that analysis.

## Why

The 2026-10-29 Zirtue nightly run (Thu) had to improvise this twice:

- `scripts/other_folders.cjs` only lists folders that are NOT the configured repos. To get the zng chat windows, the run passed a fake `--repo C:/nonexistent/x` so the zng folders showed up as "other". That is a hack.
- Whether a quiet stretch was idle on a card (excluded per the memory `feedback_clockify_dev_no_break_recall_vs_other_project_chats`) or agent runtime (counted) was checked by hand. The run wrote throwaway `sessions.cjs` and `gap.cjs` scripts in `C:\tmp\clockify-zirtue-20261029\` and inspected the jsonl. The first `sessions.cjs` read every jsonl in the folder, with no mtime filter, and timed out after 120s.
- The less-time verifier subagent then found about 29m of 3-9 minute card waits that the 10-minute gap split had missed. The proposal block shrank from 110m toward 80m after that. A script that detects "last event was an `ask_user_question` tool_use, next event is the `auq-answer`" would catch these mechanically.

## Approach

- Add `--only-configured` (or a sibling script) to `C:\Users\tecno\.claude\skills\clockify-reconciliator\scripts\other_folders.cjs`. It emits the configured repos' windows per local day, using the same 25-minute split and the same LOCAL output.
- In that mode, also emit `IDLE-ON-CARD` intervals. Detection: an assistant `mcp__cc_conductor__ask_user_question` or `AskUserQuestion` tool_use, then the next user event containing `<auq-answer`. Subtract each interval from the windows when it is longer than about 2 minutes.
- Filter jsonl files by mtime against the range before parsing. Subagent jsonls under `<session>/subagents/` stay included, because they are agent runtime.
- Update SKILL.md step 6 to call the script, and add a test next to `scripts/test_other_folders.cjs`.

## Done when

On the 2026-10-29 zng data, the script prints the zng windows with 13:06-13:41 and 14:57-15:27 marked as idle on a card, and with the shorter 15:58-16:07 and 16:09-16:16 waits marked too.
