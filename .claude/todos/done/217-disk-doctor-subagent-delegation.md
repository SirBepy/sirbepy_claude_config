<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=3106d135 -->
# disk-doctor scan phases should delegate to subagents

**Type:** skill-improvement

## Goal

Update `skills/disk-doctor/windows.md` (and `macos.md` if applicable) so the "How to run a scan" section explicitly dispatches the scan commands through a subagent instead of running them inline in the main conversation.

## Context

During a 2026-07-19 disk-doctor session (see `SCAN LOG` entry dated 2026-07-19 in `windows.md`), every scan command - the initial 5-block sweep, the second-pass drill-downs, and the newly-added repo-wide build-artifact sweep - ran directly inline in the main thread. Joe caught this after the fact: "did you do all the researches? i hope you were sending out subagents to review all the files." This violates the standing CLAUDE.md rule under "Subagent-Driven vs Inline Execution -> Context-weight axis": read-only investigation whose output gets discarded after extracting the conclusion belongs in an Explore/general-purpose subagent, not the main loop. See memory `feedback_delegate_long_system_scans.md` for the full incident writeup.

The disk-doctor skill file itself never mentioned subagent delegation anywhere in its "How to run a scan" section - it just lists PowerShell blocks to run, with no instruction on whether to run them inline or dispatch them. That's the actual gap: relying on Claude to remember the general CLAUDE.md rule mid-skill isn't reliable, per this session's evidence.

## Approach

In `skills/disk-doctor/windows.md`, under "How to run a scan", add an instruction near the top: dispatch the scan commands (the 5-block initial sweep + second-pass drill-down + build-artifact sweep) to a `general-purpose` subagent with `model: sonnet`, prompted to run the listed PowerShell blocks and return only a digested summary (dirs/caches over some threshold, e.g. 1GB, with sizes) - not raw robocopy table dumps. The main session then works from that summary to rank findings and ask judgment-call questions, same as today.

Consider whether the whole multi-round back-and-forth (find -> ask -> drill deeper) still needs the main loop to stay interactive per-round, or whether a single subagent call per round is enough. Given how conversational and Joe-steered this process was in practice (many follow-up "anything else?" rounds, each responding to the prior findings), a single subagent per round (not one giant subagent for the whole session) is probably the right granularity - avoids a monolithic subagent report while still keeping raw tabular output out of the main context.

Apply the same treatment to `macos.md` if it has an equivalent scan-command structure.

## Acceptance

- `windows.md`'s "How to run a scan" section explicitly instructs dispatching scan commands via a subagent, not running them inline.
- The instruction specifies `model: sonnet` per the CLAUDE.md subagent cost-control rule.
- Next real disk-doctor invocation should show subagent dispatch in the tool-call log for the scan phase, not direct PowerShell calls from the main thread.

## Notes

This is a process/enforcement fix, not a scan-content fix - the actual scan commands and KNOWN-SAFE/NEVER-TOUCH lists don't need to change for this todo.
- completed, commit 937f802
