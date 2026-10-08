<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=7, reconfirm-count=1, content-hash=a8fadd48 -->
<!-- duplicate-checked: hits were 427 (testing floor as a Stop-hook gate), 101 (memory rubric read gate), 1032 (send-message stop guard vs daemon-meta), 12 (shortcut skills never set complete), 21 (no chained shell commands); all share only "rule/stop/close/global" vocabulary, none covers chat self-close or idle-server shutdown -->
# Global rule: chats /close themselves when done and stop servers nobody is using

**Type:** task
**Origin:** dev

## Goal

Every Claude chat, in every project, knows two standing rules without being told per session:

1. When its task is fully done (verified, committed, nothing left for Joe to answer), it runs
   `/close` itself instead of sitting idle with a live process.
2. It stops any dev server, watcher, emulator, Docker or Gradle stack it started as soon as it no
   longer needs it, and stops a shared one it did not start only after `list_peers` shows no live
   chat using it.

Joe's stated reason (2026-10-06): save RAM/CPU on this PC.

## Context

On 2026-10-06 Joe asked Jarvis to "make sure all the chats know to /close when done" and to
"close the servers if they arent using them and if nobody is using them". Jarvis relayed it by
cross-session `SendMessage` to the 7 chats `ListAgents` could reach. That only covers chats alive
at that moment. Every chat opened later starts without it, so this needs to be a durable global
rule.

What Jarvis measured that day:
- A local zng-api (`sv.ps1` entry `zng-api:start-clean`, port 3009) plus its Docker postgres,
  localstack and sftp containers had been up ~9h with zero open connections to :3009; about 430MB.
  Jarvis stopped them on Joe's say-so.
- Several Gradle daemons (~2.4GB) were idle between builds but owned by busy mc_plugins_tag chats.
  Killing them mid-loop would fail a build, which is why rule 2 is scoped to "nobody is using it".
- Chats left alive with nothing to do still hold a `claude` process of 200-330MB each
  (`Get-Process claude`, 2026-10-05).

Existing related text: `/supervised-run` SKILL.md's Stop bullet already says to check `list_peers`
before stopping a shared entry. CLAUDE.md "Process Hygiene" already covers orphan child processes
after test/build commands, but nothing covers "stop your own server when you are done with it" or
"close the chat when the task is done". Grep of CLAUDE.md, `refs/process-hygiene.md` and this
backlog on 2026-10-06 found no existing rule or todo for either.

## Approach

- Add both rules to global CLAUDE.md, most likely under "Process Hygiene", pointing at
  `/supervised-run`'s Stop bullet for the shared-server check rather than restating it.
- Decide how rule 1 interacts with chats that end on a question card (they must NOT self-close)
  and with long-running loops like `/loop-todos` or `/autopilot` (close only after their final
  report). The exact wording is for the executing session to settle against `/close`'s own
  SKILL.md.
- Rejected: relying on Jarvis to re-broadcast this every session. It only reaches chats that are
  alive and listed in `ListAgents` at that moment; on 2026-10-06 two live zng chats were not listed
  and could not be reached at all.

## Acceptance

- A fresh chat in any project, asked "what do you do when your task is done?", answers with
  `/close` and with stopping its own servers, citing the CLAUDE.md line.
- A chat waiting on a question card for Joe does not self-close.
- Shared servers a different live chat depends on are not stopped (the `list_peers` check holds).

## Notes

- Both rules added to refs/process-hygiene.md 'Stopping what you started, and closing when done' with the question-card, long-run and active-conversation exceptions; CLAUDE.md Process Hygiene line replaced (the old dev-server PID line duplicated process-hygiene.md), budget check PASS with 1 token headroom.
